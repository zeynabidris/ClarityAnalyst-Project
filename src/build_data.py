"""Load the 4-table SQLite dump, check invariants, flatten to one order-line CSV."""
import sqlite3, pandas as pd, os
os.makedirs("data", exist_ok=True)
if os.path.exists("data/restaurant.db"): os.remove("data/restaurant.db")
con = sqlite3.connect("data/restaurant.db")
con.executescript(open("data/restaurant.sql", encoding="utf-8").read())
for t in ["menu_items","servers","orders","order_lines"]:
    print(t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
q = """
SELECT ol.id AS line_id, o.id AS order_id,
       date(o.ordered_at) AS order_date,
       CAST(strftime('%H', o.ordered_at) AS INTEGER) AS hour,
       CASE strftime('%w', o.ordered_at) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday'
         WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday'
         WHEN '5' THEN 'Friday' ELSE 'Saturday' END AS weekday,
       o.channel, o.table_no, o.covers, s.full_name AS server,
       m.dish_label AS item, m.course, ol.quantity,
       ol.unit_price, ol.unit_cost, ol.line_amount AS revenue,
       ol.line_cost AS cost, ol.line_margin AS margin
FROM order_lines ol JOIN orders o ON o.id=ol.order_id
JOIN menu_items m ON m.id=ol.item_id JOIN servers s ON s.id=o.server_id
ORDER BY ol.id"""
df = pd.read_sql(q, con)
assert (abs(df.unit_price*df.quantity - df.revenue) < 0.005).all(), "revenue != price*qty"
assert (abs(df.unit_cost*df.quantity - df.cost) < 0.005).all(), "cost != unitcost*qty"
assert (abs(df.revenue - df.cost - df.margin) < 0.005).all(), "margin != revenue-cost"
print("invariants OK; flat rows:", len(df), "orders:", df.order_id.nunique())
df.to_csv("data/sales_flat.csv", index=False)
print(df.head(3).to_string())
