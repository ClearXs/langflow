// Members API Type Definitions

export interface SpaceMembershipRead {
  id: number;
  user_id: number;
  search_space_id: number;
  role_id: number;
  created_at: string;
  updated_at: string;
  user?: {
    id: number;
    username: string;
    email: string;
  };
  role?: {
    id: number;
    name: string;
  };
}

export interface MembershipCreate {
  user_id: number;
  role_id: number;
}

export interface MembershipUpdate {
  role_id: number;
}

export interface DeleteMembershipResponse {
  message: string;
}

export interface UserSpaceAccess {
  user_id: number;
  search_space_id: number;
  role: string;
  permissions: string[];
  is_owner: boolean;
}
