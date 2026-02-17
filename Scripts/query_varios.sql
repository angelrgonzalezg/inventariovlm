select ic.location,  count(*) from inventory_count ic
group by ic.location

--
select ic.deposit_id,  count(*) from inventory_count ic
group by ic.deposit_id

select i.* from items i where 
--i.code_item like '16%' and i.current_inventory > 1
i.description_item like '%100M%';

select i.* from items i where 
--i.code_item like '16%' and i.current_inventory > 1
i.description_item like '%100M%';