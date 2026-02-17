SELECT 
       ic.code_item AS item,
       ic.location AS ubicacion, 
       MAX(i.description_item) AS item_descripcion, 
       SUM(boxunittotal) AS en_cajas, 
       SUM(ic.magazijn) AS sueltos, 
       SUM(ic.total) AS total, 
       MAX(i.current_inventory) AS inventario_actual,
       SUM(ic.total) - MAX(i.current_inventory) AS diferencia
FROM inventory_count ic
JOIN items i      ON i.code_item = ic.code_item
JOIN racks r      ON r.rack_id = ic.rack_id
JOIN deposits d   ON d.deposit_id = ic.deposit_id
GROUP BY ic.code_item, ic.location
--HAVING ABS(SUM(ic.total) - MAX(i.current_inventory)) > 100
HAVING ABS(SUM(ic.total) - MAX(i.current_inventory)) BETWEEN 20 AND 100
ORDER BY ABS(diferencia) DESC;
