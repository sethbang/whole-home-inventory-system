export interface Backup {
  id: string;
  owner_id: string;
  filename: string;
  file_path: string;
  size_bytes: number;
  item_count: number;
  image_count: number;
  created_at: string;
  status: 'completed' | 'failed' | 'in_progress' | string;
  error_message?: string;
}

export interface BackupList {
  backups: Backup[];
}

export interface RestoreResult {
  success: boolean;
  message: string;
  items_restored?: number;
  images_restored?: number;
  errors?: string[] | null;
  // v2.1 two-phase contract fields.
  dry_run?: boolean;
  current_item_count?: number | null;
  backup_item_count?: number | null;
  backup_image_count?: number | null;
}
