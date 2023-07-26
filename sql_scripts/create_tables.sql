DROP TABLE IF EXISTS alembic_version;
DROP TABLE IF EXISTS alternative;
DROP TABLE IF EXISTS 'commit';
DROP TABLE IF EXISTS entity;
DROP TABLE IF EXISTS entity_class;
DROP TABLE IF EXISTS entity_class_type;
DROP TABLE IF EXISTS entity_group;
DROP TABLE IF EXISTS entity_metadata;
DROP TABLE IF EXISTS entity_type;
DROP TABLE IF EXISTS feature;
DROP TABLE IF EXISTS list_value;
DROP TABLE IF EXISTS metadata;
DROP TABLE IF EXISTS object;
DROP TABLE IF EXISTS object_class;
DROP TABLE IF EXISTS parameter_definition;
DROP TABLE IF EXISTS parameter_definition_tag;
DROP TABLE IF EXISTS parameter_tag;
DROP TABLE IF EXISTS parameter_value;
DROP TABLE IF EXISTS parameter_value_list;
DROP TABLE IF EXISTS parameter_value_metadata;
DROP TABLE IF EXISTS relationship;
DROP TABLE IF EXISTS relationship_class;
DROP TABLE IF EXISTS relationship_entity;
DROP TABLE IF EXISTS relationship_entity_class;
DROP TABLE IF EXISTS scenario;
DROP TABLE IF EXISTS scenario_alternative;
DROP TABLE IF EXISTS tool;
DROP TABLE IF EXISTS tool_feature;
DROP TABLE IF EXISTS tool_feature_method;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
CREATE TABLE alternative (
    id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT (NULL),
    commit_id INTEGER,
    CONSTRAINT pk_alternative PRIMARY KEY (id),
    CONSTRAINT uq_alternative_name UNIQUE (name),
    CONSTRAINT fk_alternative_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE 'commit' (
    id INTEGER NOT NULL,
    comment VARCHAR(255) NOT NULL,
    date DATETIME NOT NULL,
    user VARCHAR(45),
    CONSTRAINT pk_commit PRIMARY KEY (id)
);
CREATE TABLE entity (
    id INTEGER NOT NULL,
    type_id INTEGER,
    class_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT (NULL),
    commit_id INTEGER,
    CONSTRAINT pk_entity PRIMARY KEY (id),
    CONSTRAINT uq_entity_idclass_id UNIQUE (id, class_id),
    CONSTRAINT uq_entity_idtype_idclass_id UNIQUE (id, type_id, class_id),
    CONSTRAINT uq_entity_class_idname UNIQUE (class_id, name),
    CONSTRAINT fk_entity_type_id_entity_type FOREIGN KEY(type_id) REFERENCES entity_type (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entity_class_id_entity_class FOREIGN KEY(class_id) REFERENCES entity_class (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entity_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE entity_class (
    id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT (NULL),
    display_order INTEGER DEFAULT '99',
    display_icon BIGINT DEFAULT (NULL),
    hidden INTEGER DEFAULT '0',
    commit_id INTEGER,
    CONSTRAINT pk_entity_class PRIMARY KEY (id),
    CONSTRAINT uq_entity_class_idtype_id UNIQUE (id, type_id),
    CONSTRAINT uq_entity_class_type_idname UNIQUE (type_id, name),
    CONSTRAINT fk_entity_class_type_id_entity_class_type FOREIGN KEY(type_id) REFERENCES entity_class_type (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entity_class_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE entity_class_type (
    id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_entity_class_type PRIMARY KEY (id),
    CONSTRAINT fk_entity_class_type_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE entity_group (
    id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_class_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    CONSTRAINT pk_entity_group PRIMARY KEY (id),
    CONSTRAINT uq_entity_group_entity_idmember_id UNIQUE (entity_id, member_id),
    CONSTRAINT fk_entity_group_entity_id_entity FOREIGN KEY(entity_id, entity_class_id) REFERENCES entity (id, class_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entity_group_member_id_entity FOREIGN KEY(member_id, entity_class_id) REFERENCES entity (id, class_id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE entity_metadata (
    id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    metadata_id INTEGER NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_entity_metadata PRIMARY KEY (id),
    CONSTRAINT uq_entity_metadata_entity_idmetadata_id UNIQUE (entity_id, metadata_id),
    CONSTRAINT fk_entity_metadata_entity_id_entity FOREIGN KEY(entity_id) REFERENCES entity (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entity_metadata_metadata_id_metadata FOREIGN KEY(metadata_id) REFERENCES metadata (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entity_metadata_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE entity_type (
    id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_entity_type PRIMARY KEY (id),
    CONSTRAINT fk_entity_type_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE feature (
    id INTEGER NOT NULL,
    parameter_definition_id INTEGER NOT NULL,
    parameter_value_list_id INTEGER NOT NULL,
    description TEXT DEFAULT (NULL),
    commit_id INTEGER,
    CONSTRAINT pk_feature PRIMARY KEY (id),
    CONSTRAINT uq_feature_parameter_definition_idparameter_value_list_id UNIQUE (parameter_definition_id, parameter_value_list_id),
    CONSTRAINT uq_feature_idparameter_value_list_id UNIQUE (id, parameter_value_list_id),
    CONSTRAINT fk_feature_parameter_definition_id_parameter_definition FOREIGN KEY(parameter_definition_id, parameter_value_list_id) REFERENCES parameter_definition (id, parameter_value_list_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_feature_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE list_value (
    id INTEGER NOT NULL,
    parameter_value_list_id INTEGER NOT NULL,
    'index' INTEGER NOT NULL,
    type VARCHAR(255),
    value BLOB DEFAULT (NULL),
    commit_id INTEGER,
    CONSTRAINT pk_list_value PRIMARY KEY (id),
    CONSTRAINT uq_list_value_parameter_value_list_idindex UNIQUE (parameter_value_list_id, 'index'),
    CONSTRAINT fk_list_value_parameter_value_list_id_parameter_value_list FOREIGN KEY(parameter_value_list_id) REFERENCES parameter_value_list (id),
    CONSTRAINT fk_list_value_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE metadata (
    id INTEGER NOT NULL,
    name VARCHAR(155) NOT NULL,
    value VARCHAR(255) NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_metadata PRIMARY KEY (id),
    CONSTRAINT uq_metadata_namevalue UNIQUE (name, value),
    CONSTRAINT fk_metadata_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE object (
    entity_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    CONSTRAINT pk_object PRIMARY KEY (entity_id),
    CONSTRAINT fk_object_entity_id_entity FOREIGN KEY(entity_id, type_id) REFERENCES entity (id, type_id) ON DELETE CASCADE,
    CONSTRAINT ck_object_type_id CHECK (`type_id` = 1)
);
CREATE TABLE object_class (
    entity_class_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    CONSTRAINT pk_object_class PRIMARY KEY (entity_class_id),
    CONSTRAINT fk_object_class_entity_class_id_entity_class FOREIGN KEY(entity_class_id, type_id) REFERENCES entity_class (id, type_id) ON DELETE CASCADE,
    CONSTRAINT ck_object_class_type_id CHECK (`type_id` = 1)
);
CREATE TABLE parameter_definition (
    id INTEGER NOT NULL,
    entity_class_id INTEGER NOT NULL,
    name VARCHAR(155) NOT NULL,
    description TEXT DEFAULT (NULL),
    default_type VARCHAR(255),
    default_value BLOB DEFAULT (NULL),
    commit_id INTEGER,
    parameter_value_list_id INTEGER,
    CONSTRAINT pk_parameter_definition PRIMARY KEY (id),
    CONSTRAINT uq_parameter_definition_identity_class_id UNIQUE (id, entity_class_id),
    CONSTRAINT uq_parameter_definition_entity_class_idname UNIQUE (entity_class_id, name),
    CONSTRAINT uq_parameter_definition_idparameter_value_list_id UNIQUE (id, parameter_value_list_id),
    CONSTRAINT fk_parameter_definition_entity_class_id_entity_class FOREIGN KEY(entity_class_id) REFERENCES entity_class (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_parameter_definition_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE parameter_definition_tag (
    id INTEGER NOT NULL,
    parameter_definition_id INTEGER NOT NULL,
    parameter_tag_id INTEGER NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_parameter_definition_tag PRIMARY KEY (id),
    CONSTRAINT uq_parameter_definition_tag UNIQUE (parameter_definition_id, parameter_tag_id),
    CONSTRAINT fk_parameter_tag_parameter_definition FOREIGN KEY(parameter_definition_id) REFERENCES parameter_definition (id),
    CONSTRAINT fk_parameter_definition_tag_parameter_tag_id_parameter_tag FOREIGN KEY(parameter_tag_id) REFERENCES parameter_tag (id),
    CONSTRAINT fk_parameter_definition_tag_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE parameter_tag (
    id INTEGER NOT NULL,
    tag VARCHAR(155) NOT NULL,
    description TEXT DEFAULT (NULL),
    commit_id INTEGER,
    CONSTRAINT pk_parameter_tag PRIMARY KEY (id),
    CONSTRAINT uq_parameter_tag_tag UNIQUE (tag),
    CONSTRAINT fk_parameter_tag_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE parameter_value (
    id INTEGER NOT NULL,
    parameter_definition_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_class_id INTEGER NOT NULL,
    type VARCHAR(255),
    value BLOB DEFAULT (NULL),
    commit_id INTEGER,
    alternative_id INTEGER NOT NULL,
    CONSTRAINT pk_parameter_value PRIMARY KEY (id),
    CONSTRAINT uq_parameter_value UNIQUE (parameter_definition_id, entity_id, alternative_id),
    CONSTRAINT fk_parameter_value_entity_id_entity FOREIGN KEY(entity_id, entity_class_id) REFERENCES entity (id, class_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_parameter_value_parameter_definition_id_parameter_definition FOREIGN KEY(parameter_definition_id, entity_class_id) REFERENCES parameter_definition (id, entity_class_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_parameter_value_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id),
    CONSTRAINT fk_parameter_value_alternative_id_alternative FOREIGN KEY(alternative_id) REFERENCES alternative (id)
);
CREATE TABLE parameter_value_list (
    id INTEGER NOT NULL,
    name VARCHAR(155) NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_parameter_value_list PRIMARY KEY (id),
    CONSTRAINT fk_parameter_value_list_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE parameter_value_metadata (
    id INTEGER NOT NULL,
    parameter_value_id INTEGER NOT NULL,
    metadata_id INTEGER NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_parameter_value_metadata PRIMARY KEY (id),
    CONSTRAINT uq_parameter_value_metadata_parameter_value_idmetadata_id UNIQUE (parameter_value_id, metadata_id),
    CONSTRAINT fk_parameter_value_metadata_parameter_value_id_parameter_value FOREIGN KEY(parameter_value_id) REFERENCES parameter_value (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_parameter_value_metadata_metadata_id_metadata FOREIGN KEY(metadata_id) REFERENCES metadata (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_parameter_value_metadata_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE relationship (
    entity_id INTEGER NOT NULL,
    entity_class_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    CONSTRAINT pk_relationship PRIMARY KEY (entity_id),
    CONSTRAINT uq_relationship_entity_identity_class_id UNIQUE (entity_id, entity_class_id),
    CONSTRAINT fk_relationship_entity_id_entity FOREIGN KEY(entity_id, type_id) REFERENCES entity (id, type_id) ON DELETE CASCADE,
    CONSTRAINT ck_relationship_type_id CHECK (`type_id` = 2)
);
CREATE TABLE relationship_class (
    entity_class_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    CONSTRAINT pk_relationship_class PRIMARY KEY (entity_class_id),
    CONSTRAINT fk_relationship_class_entity_class_id_entity_class FOREIGN KEY(entity_class_id, type_id) REFERENCES entity_class (id, type_id) ON DELETE CASCADE,
    CONSTRAINT ck_relationship_class_type_id CHECK (`type_id` = 2)
);
CREATE TABLE relationship_entity (
    entity_id INTEGER NOT NULL,
    entity_class_id INTEGER NOT NULL,
    dimension INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    member_class_id INTEGER NOT NULL,
    CONSTRAINT pk_relationship_entity PRIMARY KEY (entity_id, dimension),
    CONSTRAINT fk_relationship_entity_member_id_entity FOREIGN KEY(member_id, member_class_id) REFERENCES entity (id, class_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_relationship_entity_entity_class_id_relationship_entity_class FOREIGN KEY(entity_class_id, dimension, member_class_id) REFERENCES relationship_entity_class (entity_class_id, dimension, member_class_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_relationship_entity_entity_id_relationship FOREIGN KEY(entity_id, entity_class_id) REFERENCES relationship (entity_id, entity_class_id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE relationship_entity_class (
    entity_class_id INTEGER NOT NULL,
    dimension INTEGER NOT NULL,
    member_class_id INTEGER NOT NULL,
    member_class_type_id INTEGER NOT NULL,
    CONSTRAINT pk_relationship_entity_class PRIMARY KEY (entity_class_id, dimension),
    CONSTRAINT uq_relationship_entity_class UNIQUE (entity_class_id, dimension, member_class_id),
    CONSTRAINT fk_relationship_entity_class_member_class_id_entity_class FOREIGN KEY(member_class_id, member_class_type_id) REFERENCES entity_class (id, type_id),
    CONSTRAINT ck_relationship_entity_class_member_class_type_id CHECK (`member_class_type_id` != 2),
    CONSTRAINT fk_relationship_entity_class_entity_class_id_relationship_class FOREIGN KEY(entity_class_id) REFERENCES relationship_class (entity_class_id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE scenario (
    id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT (NULL),
    active BOOLEAN DEFAULT (0) NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_scenario PRIMARY KEY (id),
    CONSTRAINT uq_scenario_name UNIQUE (name),
    CONSTRAINT ck_scenario_active CHECK (active IN (0, 1)),
    CONSTRAINT fk_scenario_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE scenario_alternative (
    id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL,
    alternative_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_scenario_alternative PRIMARY KEY (id),
    CONSTRAINT uq_scenario_alternative_scenario_idrank UNIQUE (scenario_id, rank),
    CONSTRAINT uq_scenario_alternative_scenario_idalternative_id UNIQUE (scenario_id, alternative_id),
    CONSTRAINT fk_scenario_alternative_scenario_id_scenario FOREIGN KEY(scenario_id) REFERENCES scenario (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_scenario_alternative_alternative_id_alternative FOREIGN KEY(alternative_id) REFERENCES alternative (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_scenario_alternative_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE tool (
    id INTEGER NOT NULL,
    name VARCHAR(155) NOT NULL,
    description TEXT DEFAULT (NULL),
    commit_id INTEGER,
    CONSTRAINT pk_tool PRIMARY KEY (id),
    CONSTRAINT fk_tool_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE tool_feature (
    id INTEGER NOT NULL,
    tool_id INTEGER,
    feature_id INTEGER NOT NULL,
    parameter_value_list_id INTEGER NOT NULL,
    required BOOLEAN DEFAULT (0) NOT NULL,
    commit_id INTEGER,
    CONSTRAINT pk_tool_feature PRIMARY KEY (id),
    CONSTRAINT uq_tool_feature_tool_idfeature_id UNIQUE (tool_id, feature_id),
    CONSTRAINT uq_tool_feature_idparameter_value_list_id UNIQUE (id, parameter_value_list_id),
    CONSTRAINT fk_tool_feature_feature_id_feature FOREIGN KEY(feature_id, parameter_value_list_id) REFERENCES feature (id, parameter_value_list_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tool_feature_tool_id_tool FOREIGN KEY(tool_id) REFERENCES tool (id),
    CONSTRAINT ck_tool_feature_required CHECK (required IN (0, 1)),
    CONSTRAINT fk_tool_feature_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
CREATE TABLE tool_feature_method (
    id INTEGER NOT NULL,
    tool_feature_id INTEGER NOT NULL,
    parameter_value_list_id INTEGER NOT NULL,
    method_index INTEGER,
    commit_id INTEGER,
    CONSTRAINT pk_tool_feature_method PRIMARY KEY (id),
    CONSTRAINT uq_tool_feature_method_tool_feature_idmethod_index UNIQUE (tool_feature_id, method_index),
    CONSTRAINT fk_tool_feature_method_tool_feature_id_tool_feature FOREIGN KEY(tool_feature_id, parameter_value_list_id) REFERENCES tool_feature (id, parameter_value_list_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tool_feature_method_parameter_value_list_id_list_value FOREIGN KEY(parameter_value_list_id, method_index) REFERENCES list_value (parameter_value_list_id, 'index') ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tool_feature_method_commit_id_commit FOREIGN KEY(commit_id) REFERENCES 'commit' (id)
);
