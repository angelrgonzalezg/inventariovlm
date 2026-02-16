select ic.counter_name, ic.location,  count(*) 
 from inventory_count ic
group by ic.counter_name, ic.location;

select ic.counter_name,
       ic.deposit_id,  
       count(*) 
 from inventory_count ic
group by ic.counter_name, ic.deposit_id
order by ic.counter_name, ic.deposit_id;
--
select ic.deposit_id,  count(*) from inventory_count ic
group by ic.deposit_id

select i.* from items i where 
--i.code_item like '16%' and i.current_inventory > 1
i.description_item like '%48800%'