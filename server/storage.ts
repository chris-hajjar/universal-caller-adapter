import { users, type User, type InsertUser, mediaFiles, type MediaFile, type InsertMediaFile } from "@shared/schema";
import { db } from "./db";
import { eq, desc } from "drizzle-orm";

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
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user || undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db
      .insert(users)
      .values(insertUser)
      .returning();
    return user;
  }

  // Media file operations
  async getMediaFile(id: number): Promise<MediaFile | undefined> {
    const [mediaFile] = await db.select().from(mediaFiles).where(eq(mediaFiles.id, id));
    return mediaFile || undefined;
  }

  async getMediaFiles(): Promise<MediaFile[]> {
    return await db.select().from(mediaFiles).orderBy(desc(mediaFiles.createdAt));
  }

  async createMediaFile(insertFile: InsertMediaFile): Promise<MediaFile> {
    const [mediaFile] = await db
      .insert(mediaFiles)
      .values([{
        filename: insertFile.filename,
        path: insertFile.path,
        size: insertFile.size,
        mediaType: insertFile.mediaType,
        specs: insertFile.specs,
        userId: insertFile.userId
      }])
      .returning();
    return mediaFile;
  }
}

// Export a singleton instance of the storage
export const storage = new DatabaseStorage();
