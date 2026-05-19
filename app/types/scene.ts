export interface Scene {
  id: string;
  index: number;
  title: string;
  narration: string;
  visualDescription: string;
  duration: number; // seconds
  imageQuery?: string; // search query for finding/selecting an image
  imageUrl?: string; // user-picked illustration image URL
}

export interface ScenePlan {
  title: string;
  scenes: Scene[];
  totalDuration: number;
}

export interface ExtractedContent {
  title: string;
  text: string;
  source: string;
}
