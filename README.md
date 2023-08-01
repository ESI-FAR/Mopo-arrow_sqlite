# Exploring Arrow, SQlite

## Installation
In addition to the packages in the [Pipfile](./Pipfile), you need to locally install `sqlite` and `sqldiff`.

## Goals
- can we represent the Spine datastructure in Arrow?
  - e.g. expressing "relationships"
  - build against the [entity-only](https://github.com/spine-tools/Spine-Database-API/tree/issue_215_drop_object_and_relationship) branch; see: @spine-tools/Spine-Database-API#215
- look at the cache implementation 

## ADBC Tasks
1. figure out how to set the PostgreSQL URI env variable correctly ✅
   run docker: docker run --rm -p 5432:5432 --name postgres-adbc-test -e POSTGRES_PASSWORD=mysecretpassword -d postgres
   example: ADBC_POSTGRESQL_TEST_URI="postgresql://postgres:mysecretpassword@localhost:5432/postgres";
2. figure out how setup & teardown for tests work
3. a. replicate table setup for FOREIGN KEY using their test framework (steal from PRIMARY KEY) linking to a PRIMARY KEY
3. b. replicate table setup for FOREIGN KEY using their test framework (steal from PRIMARY KEY) _not_ linking to a PRIMARY KEY
5. research about how to test FOREIGN KEY elements
6. create test cases
