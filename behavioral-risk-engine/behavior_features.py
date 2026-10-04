"""Strictly prior, per-customer features. Source clock is not asserted to be local time."""
from collections import Counter,deque
from datetime import datetime,timedelta
import bisect,math

NUMERIC=['amount_percentile','amount_vs_median','amount_z_score','merchant_novelty',
 'previous_merchant_transactions','days_since_merchant_first_observed','category_novelty',
 'source_hour_rarity','transactions_previous_hour','transactions_previous_day',
 'seconds_since_previous_transaction','merchant_distance_percentile','merchant_distance_vs_median','history_count',
 'amount','source_hour','amount_vs_category_median','category_history_count']
FIELDS={'transaction_id','user_id','timestamp','amount','merchant_id','category',
        'home_latitude','home_longitude','merchant_latitude','merchant_longitude'}

def moment(value):
    t=datetime.fromisoformat(value)
    if t.tzinfo is not None:raise ValueError('Use Sparkov source-clock timestamps without a timezone')
    return t

def validate(tx):
    if not isinstance(tx,dict) or set(tx)!=FIELDS:raise ValueError('Incorrect behavioral schema')
    for name in ('transaction_id','user_id','merchant_id','category'):
        if not isinstance(tx[name],str) or not tx[name] or len(tx[name])>256:raise ValueError('Invalid identifier')
    moment(tx['timestamp'])
    for name in ('amount','home_latitude','home_longitude','merchant_latitude','merchant_longitude'):
        value=tx[name]
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):raise ValueError('Invalid number')
    if tx['amount']<=0:raise ValueError('Amount must be positive')
    for name in ('home_latitude','merchant_latitude'):
        if abs(tx[name])>90:raise ValueError('Invalid latitude')
    for name in ('home_longitude','merchant_longitude'):
        if abs(tx[name])>180:raise ValueError('Invalid longitude')

def distance(tx):
    a,b,c,d=map(math.radians,[tx['home_latitude'],tx['home_longitude'],tx['merchant_latitude'],tx['merchant_longitude']])
    h=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 6371*2*math.asin(math.sqrt(min(1,max(0,h))))

def quantile(ordered,q):
    if not ordered:return None
    p=(len(ordered)-1)*q;i=int(p);j=min(i+1,len(ordered)-1)
    return ordered[i]+(ordered[j]-ordered[i])*(p-i)

class CustomerState:
    def __init__(self):
        self.window=deque();self.day=deque();self.hour=deque();self.amounts=[];self.distances=[]
        self.hours=Counter();self.merchants=Counter();self.categories=Counter();self.first={};self.last=None
        self.total=0.;self.squared=0.
        self.category_amounts={}
    def expire(self,now):
        while self.window and self.window[0][0]<now-timedelta(days=90):
            t,a,d,c=self.window.popleft();self.amounts.pop(bisect.bisect_left(self.amounts,a));self.distances.pop(bisect.bisect_left(self.distances,d))
            values=self.category_amounts[c];values.pop(bisect.bisect_left(values,a))
            self.hours[t.hour]-=1;self.total-=a;self.squared-=a*a
        while self.hour and self.hour[0]<now-timedelta(hours=1):self.hour.popleft()
        while self.day and self.day[0]<now-timedelta(days=1):self.day.popleft()
    def observe(self,tx):
        t=moment(tx['timestamp']);a=float(tx['amount']);d=distance(tx)
        if self.last and t<self.last:raise ValueError('History must be chronological')
        self.expire(t);self.window.append((t,a,d,tx['category']));bisect.insort(self.amounts,a);bisect.insort(self.distances,d)
        bisect.insort(self.category_amounts.setdefault(tx['category'],[]),a)
        self.hours[t.hour]+=1;self.hour.append(t);self.day.append(t);self.total+=a;self.squared+=a*a
        self.merchants[tx['merchant_id']]+=1;self.categories[tx['category']]+=1
        self.first.setdefault(tx['merchant_id'],t);self.last=t
    def describe(self,tx):
        now=moment(tx['timestamp'])
        if self.last and self.last>=now:raise ValueError('Current or simultaneous transactions leaked into baseline')
        self.expire(now);n=len(self.amounts);a=tx['amount'];d=distance(tx)
        median=quantile(self.amounts,.5);p95=quantile(self.amounts,.95)
        mean=self.total/n if n else None
        sd=math.sqrt(max(0,self.squared/n-mean*mean)) if n else None
        distmedian=quantile(self.distances,.5)
        category_values=self.category_amounts.get(tx['category'],[])
        category_median=quantile(category_values,.5)
        features={'amount_percentile':bisect.bisect_right(self.amounts,a)/n if n else None,
          'amount_vs_median':a/median if median else None,'amount_z_score':(a-mean)/sd if sd and sd>1e-8 else None,
          'merchant_novelty':int(not self.merchants[tx['merchant_id']]),
          'previous_merchant_transactions':self.merchants[tx['merchant_id']],
          'days_since_merchant_first_observed':(now-self.first[tx['merchant_id']]).total_seconds()/86400 if tx['merchant_id'] in self.first else None,
          'category_novelty':int(not self.categories[tx['category']]),
          'source_hour_rarity':1-self.hours[now.hour]/n if n else None,
          'transactions_previous_hour':len(self.hour),'transactions_previous_day':len(self.day),
          'seconds_since_previous_transaction':(now-self.last).total_seconds() if self.last else None,
          'merchant_distance_percentile':bisect.bisect_right(self.distances,d)/n if n else None,
          'merchant_distance_vs_median':d/distmedian if distmedian and distmedian>1e-8 else None,'history_count':n,
          'amount':a,'source_hour':now.hour,'amount_vs_category_median':a/category_median if category_median else None,
          'category_history_count':len(category_values)}
        signals=[]
        def add(test,kind,points,explanation):
            if test:signals.append({'type':kind,'points':points,'explanation':explanation})
        add(n>=20 and a>p95,'LARGE_FOR_CUSTOMER',25,f'Amount {a:.2f}; prior 90-day median {median or 0:.2f}, 95th percentile {p95 or 0:.2f}.')
        add(n>=20 and features['amount_vs_median']>5,'MUCH_LARGER_THAN_MEDIAN',15,'Amount exceeds five times this customer’s prior median.')
        add(n>=20 and features['merchant_novelty'],'UNSEEN_MERCHANT',15,'No earlier observed payment to this merchant. This is not a newly registered bank payee.')
        add(n>=20 and features['category_novelty'],'UNSEEN_CATEGORY',10,'Purchase category absent from prior observations.')
        add(n>=20 and self.hours[now.hour]==0,'UNUSUAL_SOURCE_CLOCK_HOUR',10,'No observation at this source-clock hour in the prior 90 days; local timezone is unknown.')
        add(n>=20 and d>quantile(self.distances,.95),'UNUSUAL_MERCHANT_DISTANCE',10,'Merchant-to-home distance exceeds the prior 90-day 95th percentile; this is not device/IP location.')
        add(n>=20 and len(self.hour)>=3,'RAPID_PAYMENTS',15,'At least three earlier payments in the preceding hour.')
        return features,{'history_count':n,'window_days':90,'median_amount':median,'p95_amount':p95,
                         'prior_merchant_payments':self.merchants[tx['merchant_id']],'merchant_distance_km':d,
                         'category_median_amount':category_median,'category_history_count':len(category_values)},signals

def from_history(tx,history):
    validate(tx);now=moment(tx['timestamp']);state=CustomerState()
    rows=[r for r in history if r['user_id']==tx['user_id'] and r['transaction_id']!=tx['transaction_id'] and moment(r['timestamp'])<now]
    for row in sorted(rows,key=lambda r:(r['timestamp'],r['transaction_id'])):state.observe(row)
    return state.describe(tx)
