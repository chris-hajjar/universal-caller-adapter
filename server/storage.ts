import { users, type User, type InsertUser, mediaFiles, type MediaFile, type InsertMediaFile } from "@shared/schema";
import { db } from "./db";
import { eq, desc, sql } from "drizzle-orm";

// Interface for storage operations
export interface IStorage {
  // User operations
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  // Media file operations
  getMediaFile(id: number): Promise<MediaFile | undefined>;
  getMediaFiles(): Promise<MediaFile[]>;
  createMediaFile(file: InsertMediaFile): Promise<MediaFile>;
}

// Database storage implementation
export class DatabaseStorage implements IStorage {
  // User operations
  async getUser(id: number): Promise<User | undefined> {
    const result = await db.select().from(users).where(eq(users.id, id));
    return result.length > 0 ? result[0] : undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const result = await db.select().from(users).where(eq(users.username, username));
    return result.length > 0 ? result[0] : undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const result = await db
      .insert(users)
      .values(insertUser)
      .returning();
    return result[0];
  }

  // Media file operations
  async getMediaFile(id: number): Promise<MediaFile | undefined> {
    const result = await db.select().from(mediaFiles).where(eq(mediaFiles.id, id));
    return result.length > 0 ? result[0] : undefined;
  }

  async getMediaFiles(): Promise<MediaFile[]> {
    return await db.select().from(mediaFiles).orderBy(desc(mediaFiles.createdAt));
  }

  async createMediaFile(insertFile: InsertMediaFile): Promise<MediaFile> {
    // Use a raw SQL query to bypass TypeScript type issues
    // This is a workaround for the current TypeScript errors
    const result = await db.execute(
      sql`INSERT INTO media_files (filename, path, size, media_type, specs, user_id) 
          VALUES (${insertFile.filename}, ${insertFile.path}, ${insertFile.size}, 
                  ${insertFile.mediaType}, ${JSON.stringify(insertFile.specs)}, ${insertFile.userId || null})
          RETURNING *`
    );
    
    return result.rows[0] as unknown as MediaFile;
  }
}

// Export a singleton instance of the storage
export const storage = new DatabaseStorage();
