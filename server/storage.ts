import { users, type User, type InsertUser, mediaFiles, type MediaFile, type InsertMediaFile } from "@shared/schema";

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

// In-memory storage implementation
export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private mediaFiles: Map<number, MediaFile>;
  private currentUserId: number;
  private currentMediaFileId: number;

  constructor() {
    this.users = new Map();
    this.mediaFiles = new Map();
    this.currentUserId = 1;
    this.currentMediaFileId = 1;
  }

  // User operations
  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.currentUserId++;
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  // Media file operations
  async getMediaFile(id: number): Promise<MediaFile | undefined> {
    return this.mediaFiles.get(id);
  }

  async getMediaFiles(): Promise<MediaFile[]> {
    return Array.from(this.mediaFiles.values())
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }

  async createMediaFile(insertFile: InsertMediaFile): Promise<MediaFile> {
    const id = this.currentMediaFileId++;
    const mediaFile: MediaFile = { 
      ...insertFile, 
      id, 
      createdAt: new Date().toISOString() 
    };
    this.mediaFiles.set(id, mediaFile);
    return mediaFile;
  }
}

// Export a singleton instance of the storage
export const storage = new MemStorage();
