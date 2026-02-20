select ic.code_item item, 
       ic.count_date,
       i.description_item item_description, 
       ic.total
  from inventory_count ic, items i
 where i.code_item = ic.code_item
 and ic.total != 0
 order by ic.code_item, ic.count_date 
   

select ic.code_item item, 
       max(i.description_item) item_description, 
       sum(ic.total) Total
  from inventory_count ic, items i
 where i.code_item = ic.code_item
 and ic.total != 0
 group by ic.code_item
 order by ic.code_item




select ic.location As Ubicacion,
       ic.code_item AS Codigo, 
       i.description_item AS Descripcion,
       ic.total AS  Inventario,
       i.current_inventory AS Actual_total_item
  from inventory_count ic, items i
 where i.code_item = ic.code_item
 order by ic.location, ic.code_item, ic.count_date 
