select 
--d.deposit_description, r.rack_description,
ic.location ubicacion, 
 ic.code_item item, 
 i.description_item item_descripcion, 
 ic.boxqty, ic.boxunitqty, ic.boxunittotal, ic.magazijn, ic.total, i.current_inventory, i.current_inventory - ic.total as diferencia 
  from inventory_count ic, items i, racks r, deposits d
 where i.code_item = ic.code_item
   and r.rack_id = ic.rack_id
   and d.deposit_id = ic.deposit_id;

select ic.code_item item,
       ic.location ubicacion, 
       max(i.description_item) item_descripcion, 
       sum(boxunittotal) en_cajas, 
       sum(ic.magazijn) sueltos, 
       sum(ic.total) total, 
       max(i.current_inventory) inventario_actual,
       SUM(ic.total)  - MAX(i.current_inventory) AS diferencia
  from inventory_count ic, items i, racks r, deposits d
 where i.code_item = ic.code_item
   and r.rack_id = ic.rack_id
   and d.deposit_id = ic.deposit_id
   and i.code_item = '1805'
      group by ic.code_item, ic.location
      
select ic.code_item item,
--       ic.location ubicacion, 
       max(i.description_item) item_descripcion, 
       sum(boxunittotal) en_cajas, 
       sum(ic.magazijn) sueltos, 
       sum(ic.total) total, 
       max(i.current_inventory) inventario_actual,
       SUM(ic.total)  - MAX(i.current_inventory) AS diferencia
  from inventory_count ic, items i, racks r, deposits d
 where i.code_item = ic.code_item
   and r.rack_id = ic.rack_id
   and d.deposit_id = ic.deposit_id
   and ic.code_item = '0101'
   --and ic.location = 'Deposit N3-A1'
   group by ic.code_item;
   


select ic.code_item item,
       --i.description_item item_descripcion, 
       ic.boxunittotal en_cajas, 
       ic.magazijn sueltos, 
       ic.total total 
       --i.current_inventory inventario_actual,
       --ic.total  - i.current_inventory AS diferencia
  from inventory_count ic
  --, items i, racks r, deposits d
 where
 -- i.code_item = ic.code_item
  -- and r.rack_id = ic.rack_id
  -- and d.deposit_id = ic.deposit_id
    ic.code_item = '0101'
   --and ic.location = 'Deposit N3-A1'
--   group by ic.code_item














