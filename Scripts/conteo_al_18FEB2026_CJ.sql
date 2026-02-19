select ic.code_item item, 
       ic.count_date,
       i.description_item item_description, 
       ic.total
  from inventory_count ic, items i
 where i.code_item = ic.code_item
 and ic.total != 0
 order by ic.code_item, ic.count_date 
   --and r.rack_id = ic.rack_id
   --and d.deposit_id = ic.deposit_id;
   

select ic.location,
       ic.code_item item, 
       i.description_item item_description
  from inventory_count ic, items i
  --, racks r, deposit d
 where i.code_item = ic.code_item
-- and ic.total != 0
and deposit_id <> 6
 order by ic.location, ic.code_item, ic.count_date 
 --  and r.rack_id = ic.rack_id
 --  and d.deposit_id = ic.deposit_id;
   
