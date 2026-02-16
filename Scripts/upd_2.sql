select ic.* from inventory_count ic where id >= 985
order by ic.id
--
update inventory_count   set location ='Deposit N2 - B5', deposit_id=2, rack_id=5, count_date='2026-01-27'
 where id >= 995