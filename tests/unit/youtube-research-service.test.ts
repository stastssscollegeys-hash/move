import { YouTubeResearchService } from '../../src/youtube-research/service';
import { VideoMeta, BuzzResult } from '../../src/youtube-research/types';

// Mock Anthropic SDK
jest.mock('@anthropic-ai/sdk', () => {
  return jest.fn().mockImplementation(() => ({
    messages: {
      create: jest.fn().mockResolvedValue({
        content: [{ type: 'text', text: '{}' }]
      })
    }
  }));
});

describe('YouTubeResearchService', () => {
  let service: YouTubeResearchService;

  beforeEach(() => {
    service = new YouTubeResearchService('test-api-key');
  });

  describe('fetchVideoMetadata', () => {
    it('should parse URL inputs', async () => {
      const result = await service.fetchVideoMetadata([
        { rawText: 'https://youtube.com/watch?v=abc123', inputType: 'url' }
      ]);
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('video_001');
      expect(result[0].url).toBe('https://youtube.com/watch?v=abc123');
    });

    it('should parse text inputs', async () => {
      const result = await service.fetchVideoMetadata([
        { rawText: 'AI副業の始め方について解説した動画', inputType: 'summary' }
      ]);
      expect(result).toHaveLength(1);
      expect(result[0].transcriptOrSummary).toBe('AI副業の始め方について解説した動画');
      expect(result[0].url).toBeNull();
    });

    it('should handle multiple inputs', async () => {
      const result = await service.fetchVideoMetadata([
        { rawText: 'https://youtu.be/abc', inputType: 'url' },
        { rawText: 'テスト要約', inputType: 'summary' },
        { rawText: 'https://youtube.com/watch?v=xyz', inputType: 'url' }
      ]);
      expect(result).toHaveLength(3);
      expect(result[0].id).toBe('video_001');
      expect(result[2].id).toBe('video_003');
    });
  });

  describe('detectBuzz', () => {
    it('should calculate buzz ratio correctly', async () => {
      const videos: VideoMeta[] = [
        createVideo('1', 'バズ動画', 500000, 5000),   // ratio 100 = super-buzz
        createVideo('2', '普通動画', 10000, 10000),    // ratio 1 = average
        createVideo('3', 'まあまあ動画', 30000, 10000), // ratio 3 = good
      ];

      const result = await service.detectBuzz(videos);
      expect(result.success).toBe(true);

      const ranking = result.data!.ranking;
      // Should be sorted by buzz ratio descending
      expect(ranking[0].video.title).toBe('バズ動画');
      expect(ranking[0].buzzRatio).toBe(100);
      expect(ranking[0].buzzLevel).toBe('super-buzz');

      expect(ranking[1].video.title).toBe('まあまあ動画');
      expect(ranking[1].buzzRatio).toBe(3);
      expect(ranking[1].buzzLevel).toBe('good');

      expect(ranking[2].video.title).toBe('普通動画');
      expect(ranking[2].buzzRatio).toBe(1);
      expect(ranking[2].buzzLevel).toBe('average');
    });

    it('should handle videos with no metrics', async () => {
      const videos: VideoMeta[] = [
        createVideo('1', 'メトリクスなし', null, null),
      ];

      const result = await service.detectBuzz(videos);
      expect(result.data!.ranking[0].buzzLevel).toBe('unknown');
      expect(result.data!.ranking[0].buzzRatio).toBeNull();
    });

    it('should classify buzz levels correctly', async () => {
      const testCases = [
        { views: 100000, subs: 1000, expected: 'super-buzz' },  // 100
        { views: 50000, subs: 10000, expected: 'buzz' },         // 5
        { views: 30000, subs: 10000, expected: 'good' },         // 3
        { views: 15000, subs: 10000, expected: 'average' },      // 1.5
        { views: 5000, subs: 10000, expected: 'low' },           // 0.5
      ];

      for (const tc of testCases) {
        const videos = [createVideo('t', 'test', tc.views, tc.subs)];
        const result = await service.detectBuzz(videos);
        expect(result.data!.ranking[0].buzzLevel).toBe(tc.expected);
      }
    });

    it('should handle zero subscribers', async () => {
      const videos = [createVideo('1', 'ゼロ登録者', 1000, 0)];
      const result = await service.detectBuzz(videos);
      expect(result.data!.ranking[0].buzzLevel).toBe('unknown');
    });
  });
});

function createVideo(id: string, title: string, views: number | null, subscribers: number | null): VideoMeta {
  return {
    id,
    title,
    channel: 'テストチャンネル',
    subscribers,
    views,
    likes: null,
    uploadDate: null,
    duration: null,
    description: '',
    transcriptOrSummary: '',
    url: null
  };
}
