"""Compute each benchmark answer twice (SQL on the 4 tables, pandas on the flat CSV) and keep only matches."""
import sqlite3, pandas as pd, json
con = sqlite3.connect("data/restaurant.db")
df = pd.read_csv("data/sales_flat.csv")
def sql(q): return con.execute(q).fetchall()
WD = "CASE strftime('%w',o.ordered_at) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' ELSE 'Saturday' END"
Q = []
def add(id, typ, question, s, p, kind):
    Q.append(dict(id=id, type=typ, question=question, sql=s, pandas=p, kind=kind))

# SQL result -> python, pandas result -> python, compared
res = []
def top1(rows): return rows[0]
# Q1 total revenue
s = sql("SELECT ROUND(SUM(line_amount),2) FROM order_lines")[0][0]
p = round(df.revenue.sum(),2); res.append(("Q1","simple","What was the total revenue across all orders?",s,p,"number"))
# Q2 top item by revenue
r = sql("SELECT m.dish_label, ROUND(SUM(ol.line_amount),2) t FROM order_lines ol JOIN menu_items m ON m.id=ol.item_id GROUP BY 1 ORDER BY t DESC LIMIT 2")
g = df.groupby("item").revenue.sum().round(2).sort_values(ascending=False)
res.append(("Q2","simple","Which menu item had the highest total revenue, and how much was it?",list(r[0]),[g.index[0],g.iloc[0]],"name+number")); t2=(r,g.head(2).to_dict())
# Q3 weekday with most orders
r = sql(f"SELECT {WD} d, COUNT(*) c FROM orders o GROUP BY 1 ORDER BY c DESC LIMIT 3")
g = df.groupby("weekday").order_id.nunique().sort_values(ascending=False)
res.append(("Q3","simple","Which weekday had the most orders, and how many?",list(r[0]),[g.index[0],int(g.iloc[0])],"name+number")); t3=(r,g.head(3).to_dict())
# Q4 course with highest margin
r = sql("SELECT m.course, ROUND(SUM(ol.line_margin),2) t FROM order_lines ol JOIN menu_items m ON m.id=ol.item_id GROUP BY 1 ORDER BY t DESC LIMIT 2")
g = df.groupby("course").margin.sum().round(2).sort_values(ascending=False)
res.append(("Q4","multi-step","Which course earned the highest total margin, and what was it?",list(r[0]),[g.index[0],g.iloc[0]],"name+number")); t4=(r,g.head(2).to_dict())
# Q5 hour with highest revenue
r = sql("SELECT CAST(strftime('%H',o.ordered_at) AS INT) h, ROUND(SUM(ol.line_amount),2) t FROM order_lines ol JOIN orders o ON o.id=ol.order_id GROUP BY 1 ORDER BY t DESC LIMIT 3")
g = df.groupby("hour").revenue.sum().round(2).sort_values(ascending=False)
res.append(("Q5","multi-step","Which hour of the day had the highest total revenue, and how much was it?",list(r[0]),[int(g.index[0]),g.iloc[0]],"name+number")); t5=(r,g.head(3).to_dict())
# Q7 first 4 weeks vs last 4 weeks biggest item drop
r = sql("""SELECT m.dish_label,
  ROUND(SUM(CASE WHEN date(o.ordered_at)<'2025-03-31' THEN ol.line_amount ELSE 0 END),2) a,
  ROUND(SUM(CASE WHEN date(o.ordered_at)>='2025-03-31' THEN ol.line_amount ELSE 0 END),2) b
  FROM order_lines ol JOIN orders o ON o.id=ol.order_id JOIN menu_items m ON m.id=ol.item_id GROUP BY 1
  ORDER BY (b-a) ASC LIMIT 3""")
df["d"]=pd.to_datetime(df.order_date); first=df[df.d<"2025-03-31"].groupby("item").revenue.sum(); last=df[df.d>="2025-03-31"].groupby("item").revenue.sum()
ch=(last.reindex(first.index,fill_value=0)-first).round(2).sort_values()
res.append(("Q6","multi-step","Which menu item had the biggest drop in revenue from the first four weeks to the last four weeks, and by how much?",[r[0][0],round(r[0][2]-r[0][1],2)],[ch.index[0],ch.iloc[0]],"name+number")); t7=(r,ch.head(3).to_dict())
print("date range:", sql("SELECT MIN(ordered_at),MAX(ordered_at) FROM orders"))
print("weeks split check:", sql("SELECT COUNT(*) FROM orders WHERE date(ordered_at)<'2025-03-31'"), sql("SELECT COUNT(*) FROM orders WHERE date(ordered_at)>='2025-03-31'"))
for k,v in {"Q2":t2,"Q3":t3,"Q4":t4,"Q5":t5,"Q6":t7}.items(): print(k, v)
for r_ in res: print(r_[0], r_[3], r_[4], "MATCH" if r_[3]==r_[4] or (isinstance(r_[3],list) and r_[3][0]==r_[4][0] and abs(r_[3][1]-r_[4][1])<0.01) or (not isinstance(r_[3],list) and abs(r_[3]-r_[4])<0.01) else "MISMATCH")
print("channels:", sql("SELECT channel, COUNT(*) FROM orders GROUP BY 1"))
