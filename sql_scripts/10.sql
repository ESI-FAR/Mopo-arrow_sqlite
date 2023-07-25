UPDATE "commit" SET comment='commit many changes', date='2023-07-25 09:43:05.816613' WHERE id=4;
INSERT INTO entity(id,type_id,class_id,name,description,commit_id) VALUES(2,1,3,'power_plant','A single power plant',4);
INSERT INTO entity(id,type_id,class_id,name,description,commit_id) VALUES(3,2,4,'unit__from_node_power_plant__fuel_node',NULL,4);
INSERT INTO object(entity_id,type_id) VALUES(2,1);
INSERT INTO parameter_value(id,parameter_definition_id,entity_id,entity_class_id,type,value,commit_id,alternative_id) VALUES(1,1,1,2,'list_value_ref',x'32',4,1);
INSERT INTO relationship(entity_id,entity_class_id,type_id) VALUES(3,4,2);
INSERT INTO relationship_entity(rowid,entity_id,entity_class_id,dimension,member_id,member_class_id) VALUES(1,3,4,0,2,3);
INSERT INTO relationship_entity(rowid,entity_id,entity_class_id,dimension,member_id,member_class_id) VALUES(2,3,4,1,1,2);
