UPDATE "commit" SET comment='add fuel node', date='2023-07-25 09:35:46.420410' WHERE id=3;
INSERT INTO entity(id,type_id,class_id,name,description,commit_id) VALUES(1,1,2,'fuel_node','A single fuel node',3);
INSERT INTO object(entity_id,type_id) VALUES(1,1);
