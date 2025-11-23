-- Rename mimesis_transformations to persona_transformations
-- This migration renames the table and its indexes for clarity and consistency

-- Rename table
ALTER TABLE mimesis_transformations 
RENAME TO persona_transformations;

-- Rename indexes
ALTER INDEX idx_mimesis_transformations_ready 
RENAME TO idx_persona_transformations_ready;

-- Rollback (for reference):
-- ALTER TABLE persona_transformations RENAME TO mimesis_transformations;
-- ALTER INDEX idx_persona_transformations_ready RENAME TO idx_mimesis_transformations_ready;

