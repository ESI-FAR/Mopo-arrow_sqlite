INSERT INTO "commit"(id,comment,date,user) VALUES(6,'edit value'||X'0a0a'
||'also a multi-line commit message','2023-07-26 08:03:51.827715','anon');
UPDATE parameter_value SET value=x'35302e30', commit_id=6 WHERE id=2;
