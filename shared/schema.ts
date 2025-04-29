import { pgTable, text, serial, integer, jsonb, timestamp, primaryKey, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";
import { relations } from "drizzle-orm";

// Schema for media file specifications (FFmpeg output)
export interface MediaFileSpecs {
  format: {
    filename?: string;
    nb_streams?: number;
    format_name?: string;
    format_long_name?: string;
    start_time?: string;
    duration?: string;
    size?: string;
    bit_rate?: string;
    [key: string]: any;
  };
  streams?: Array<{
    index?: number;
    codec_name?: string;
    codec_long_name?: string;
    codec_type?: string;
    codec_tag_string?: string;
    width?: number;
    height?: number;
    r_frame_rate?: string;
    avg_frame_rate?: string;
    time_base?: string;
    bit_rate?: string;
    sample_rate?: string;
    channels?: number;
    channel_layout?: string;
    pix_fmt?: string;
    color_space?: string;
    profile?: string;
    display_aspect_ratio?: string;
    tags?: {
      language?: string;
      [key: string]: any;
    };
    [key: string]: any;
  }>;
}

// Schema for re-encoding options
export const bitrateFormatSchema = z.string().regex(/^\d+(k|M)?$/, {
  message: "Bitrate must be a number followed by 'k' (kbps) or 'M' (Mbps), e.g., '5000k' or '5M'"
});

export type BitrateFormat = z.infer<typeof bitrateFormatSchema>;

// Schema for re-encoding request
export const reEncodeRequestSchema = z.object({
  mediaFileId: z.number(),
  targetBitrate: bitrateFormatSchema
});

export type ReEncodeRequest = z.infer<typeof reEncodeRequestSchema>;

// Users schema
export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

// Media files schema
export const mediaFiles = pgTable("media_files", {
  id: serial("id").primaryKey(),
  filename: text("filename").notNull(),
  path: text("path").notNull(),
  size: integer("size").notNull(),
  mediaType: text("media_type").notNull(), // 'audio' or 'video'
  specs: jsonb("specs").$type<MediaFileSpecs>().notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  userId: integer("user_id").references(() => users.id, { onDelete: 'set null' }),
  // Re-encoded version fields
  reEncodedPath: text("re_encoded_path"),
  reEncodedSize: integer("re_encoded_size"),
  reEncodedBitrate: text("re_encoded_bitrate"),
  isReEncoded: boolean("is_re_encoded").default(false),
});

// Define relations
export const usersRelations = relations(users, ({ many }) => ({
  mediaFiles: many(mediaFiles),
}));

export const mediaFilesRelations = relations(mediaFiles, ({ one }) => ({
  user: one(users, {
    fields: [mediaFiles.userId],
    references: [users.id],
  }),
}));

// Zod schema for creating a media file
export const insertMediaFileSchema = createInsertSchema(mediaFiles).omit({
  id: true,
  createdAt: true,
  reEncodedPath: true,
  reEncodedSize: true,
  reEncodedBitrate: true,
  isReEncoded: true,
});

export type InsertMediaFile = z.infer<typeof insertMediaFileSchema>;
export type MediaFile = typeof mediaFiles.$inferSelect;

// Zod schema for creating a user
export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
