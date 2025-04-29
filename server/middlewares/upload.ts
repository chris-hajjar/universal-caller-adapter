import multer from "multer";
import path from "path";
import fs from "fs";
import { promisify } from "util";

// Promisify file operations for async usage
const fsExists = promisify(fs.exists);
const fsMkdir = promisify(fs.mkdir);

// Cache temp directory path
const TEMP_DIR = path.join(process.cwd(), "tmp");

// Ensure temp directory exists (executed once during import)
if (!fs.existsSync(TEMP_DIR)) {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
}

// Optimized file extension check using Set for O(1) lookups
const ALLOWED_EXTENSIONS = new Set(['.mp3', '.mp4']);
// Map of mime types to extensions for validation
const MIME_TYPE_MAP: Record<string, string> = {
  'audio/mpeg': '.mp3',
  'audio/mp3': '.mp3',
  'video/mp4': '.mp4'
};

// Setup optimized multer storage
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    // Directory is already ensured to exist
    cb(null, TEMP_DIR);
  },
  filename: function (req, file, cb) {
    // More efficient unique filename generation
    const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    // Extract extension from mime type for better security
    const ext = MIME_TYPE_MAP[file.mimetype] || path.extname(file.originalname).toLowerCase();
    cb(null, `${file.fieldname}-${uniqueSuffix}${ext}`);
  }
});

// Optimized file filter with better error messages - fixed TypeScript issues
const fileFilter = (req: any, file: any, cb: any) => {
  const ext = path.extname(file.originalname).toLowerCase();
  const mimeTypeValid = !!MIME_TYPE_MAP[file.mimetype];
  const extensionValid = ALLOWED_EXTENSIONS.has(ext);
  
  if (mimeTypeValid && extensionValid) {
    cb(null, true);
  } else {
    // More informative error
    const errorMsg = `File type not supported. Only MP3 and MP4 files are allowed. Received: ${file.mimetype}, extension: ${ext}`;
    cb(new Error(errorMsg));
  }
};

// Configure the multer middleware with increased size limit
export const uploadMiddleware = multer({
  storage: storage,
  fileFilter: fileFilter,
  limits: {
    fileSize: 200 * 1024 * 1024, // 200MB in bytes (increased as requested)
  }
});
