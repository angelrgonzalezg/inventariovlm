select ic.code_item, ic.location, ic.counter_name, ic.boxqty, ic.boxunitqty, ic.magazijn, ic.total from inventory_count ic
where (ic.boxqty * ic.boxunitqty) + ic.magazijn <> ic.total;

select ic.code_item, ic.location, ic.counter_name, ic.boxqty, ic.boxunitqty, ic.magazijn, ic.total from inventory_count ic
where  ic.total = 0;
