select ic.*
  from inventory_count ic
 where ic.code_item >= '013%' and  ic.code_item < '0160'
      group by ic.code_item, ic.location