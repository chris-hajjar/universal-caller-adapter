import { Express as ExpressType } from 'express-serve-static-core';

declare global {
  namespace Express {
    // This will make the File type compatible with req.file
    interface Request {
      file?: {
        fieldname: string;
        originalname: string;
        encoding: string;
        mimetype: string;
        size: number;
        destination: string;
        filename: string;
        path: string;
        buffer: Buffer;
      };
    }
  }
}