select ic.deposit_id, ic.rack_id, ic.location, ic.* from inventory_count ic
where ic.rack_id=66 and ic.location='Almacen - L'
order by ic.deposit_id, ic.rack_id, ic.location



select count(*) from inventory_count ic