// Invites API Type Definitions

export interface SpaceInviteRead {
  id: number;
  search_space_id: number;
  invite_code: string;
  role_id: number;
  invited_by_user_id: number;
  max_uses: number | null;
  current_uses: number;
  expires_at: string | null;
  created_at: string;
  is_active: boolean;
  role?: {
    id: number;
    name: string;
  };
}

export interface SpaceInviteCreate {
  role_id: number;
  max_uses?: number | null;
  expires_at?: string | null;
}

export interface InviteUpdate {
  role_id?: number;
  max_uses?: number | null;
  expires_at?: string | null;
  is_active?: boolean;
}

export interface InviteInfoResponse {
  space_name: string;
  role_name: string;
  invited_by: string;
  expires_at: string | null;
  is_valid: boolean;
}

export interface InviteAcceptRequest {
  invite_code: string;
}

export interface InviteAcceptResponse {
  message: string;
  membership: {
    id: number;
    search_space_id: number;
    role_id: number;
  };
}

export interface DeleteInviteResponse {
  message: string;
}
