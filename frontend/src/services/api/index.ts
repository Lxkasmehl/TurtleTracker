/**
 * API Service – barrel export for backend communication
 */

// Config & token
export {
  AUTH_API_BASE_URL,
  TURTLE_API_BASE_URL,
  getToken,
  setToken,
  removeToken,
} from './config';

// Auth
export {
  apiRequest,
  register,
  login,
  getCurrentUser,
  logout,
  getGoogleAuthUrl,
  getInvitationDetails,
  promoteToAdmin,
} from './auth';
export type {
  User,
  AuthResponse,
  RegisterRequest,
  LoginRequest,
  InvitationDetails,
  PromoteToAdminResponse,
} from './auth';

// Turtle (upload, review queue)
export {
  uploadTurtlePhoto,
  getReviewQueue,
  approveReview,
  deleteReviewItem,
  getImageUrl,
} from './turtle';
export type {
  TurtleMatch,
  UploadPhotoResponse,
  LocationHint,
  ReviewQueueItem,
  ReviewQueueResponse,
  ApproveReviewRequest,
  ApproveReviewResponse,
} from './turtle';

// Sheets
export {
  getTurtleSheetsData,
  createTurtleSheetsData,
  updateTurtleSheetsData,
  generatePrimaryId,
  listSheets,
  createSheet,
  listAllTurtlesFromSheets,
} from './sheets';
export type {
  TurtleSheetsData,
  GetTurtleSheetsDataResponse,
  ListSheetsResponse,
  GeneratePrimaryIdRequest,
  GeneratePrimaryIdResponse,
  CreateTurtleSheetsDataRequest,
  CreateTurtleSheetsDataResponse,
  UpdateTurtleSheetsDataRequest,
  UpdateTurtleSheetsDataResponse,
  CreateSheetRequest,
  CreateSheetResponse,
  ListTurtlesResponse,
} from './sheets';
