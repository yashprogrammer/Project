export type ChunkMetadata = {
  chunk_id: string;
  document_id: string;
  department_id: string;
  tenant_id?: string;
  chunk_index: number;
  score: number;
  file_name: string;
};

