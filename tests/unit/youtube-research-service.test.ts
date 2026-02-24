import { VideoMeta, BuzzResult } from '../../src/youtube-research/types';

// Mock Anthropic SDK before importing service
jest.mock('@anthropic-ai/sdk', () => {
  return {
    __esModule: true,
    default: jest.fn().mockImplementation(() => ({
      messages: {
        create: jest.fn().mockResolvedValue({
          content: [{ type: 'text', text: '{}' }]
        })
      }
    }))
  };
});

// Import after mock
import { calculateBuzzForVideo, YouTubeResearchService } from '../../src/youtube-research/service';

// Helper to create a minimal VideoMeta
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
    tags: [],
    transcriptOrSummary: '',
    url: null
  };
}

describe('calculateBuzzForVideo', () => {
  it('should return super-buzz for ratio >= 10', () => {
    const video = createVideo('1', 'Test', 50000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(50);
    expect(result.buzzLevel).toBe('super-buzz');
  });

  it('should return buzz for ratio >= 5 and < 10', () => {
    const video = createVideo('1', 'Test', 7000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(7);
    expect(result.buzzLevel).toBe('buzz');
  });

  it('should return good for ratio >= 2 and < 5', () => {
    const video = createVideo('1', 'Test', 3000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(3);
    expect(result.buzzLevel).toBe('good');
  });

  it('should return average for ratio >= 1 and < 2', () => {
    const video = createVideo('1', 'Test', 1500, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(1.5);
    expect(result.buzzLevel).toBe('average');
  });

  it('should return low for ratio < 1', () => {
    const video = createVideo('1', 'Test', 500, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(0.5);
    expect(result.buzzLevel).toBe('low');
  });

  it('should return unknown when subscribers is 0', () => {
    const video = createVideo('1', 'Test', 1000, 0);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBeNull();
    expect(result.buzzLevel).toBe('unknown');
  });

  it('should return unknown when subscribers is null', () => {
    const video = createVideo('1', 'Test', 1000, null);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBeNull();
    expect(result.buzzLevel).toBe('unknown');
  });

  it('should return unknown when views is null', () => {
    const video = createVideo('1', 'Test', null, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBeNull();
    expect(result.buzzLevel).toBe('unknown');
  });

  it('should handle very large numbers', () => {
    const video = createVideo('1', 'Test', 100_000_000, 1_000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(100000);
    expect(result.buzzLevel).toBe('super-buzz');
  });

  // Boundary values
  it('should return super-buzz at exact boundary ratio = 10', () => {
    const video = createVideo('1', 'Test', 10000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(10);
    expect(result.buzzLevel).toBe('super-buzz');
  });

  it('should return buzz at exact boundary ratio = 5', () => {
    const video = createVideo('1', 'Test', 5000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(5);
    expect(result.buzzLevel).toBe('buzz');
  });

  it('should return good at exact boundary ratio = 2', () => {
    const video = createVideo('1', 'Test', 2000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(2);
    expect(result.buzzLevel).toBe('good');
  });

  it('should return average at exact boundary ratio = 1', () => {
    const video = createVideo('1', 'Test', 1000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.buzzRatio).toBe(1);
    expect(result.buzzLevel).toBe('average');
  });

  it('should include the original video in result', () => {
    const video = createVideo('v1', 'My Video', 5000, 1000);
    const result = calculateBuzzForVideo(video);
    expect(result.video).toBe(video);
    expect(result.video.id).toBe('v1');
  });
});

describe('YouTubeResearchService', () => {
  let service: YouTubeResearchService;

  beforeEach(() => {
    service = new YouTubeResearchService('sk-ant-test-key-for-testing-purposes');
  });

  describe('extractJson', () => {
    it('should return plain JSON as-is', () => {
      const input = '{"key": "value"}';
      expect(service.extractJson(input)).toBe('{"key": "value"}');
    });

    it('should strip ```json code fence', () => {
      const input = '```json\n{"key": "value"}\n```';
      expect(service.extractJson(input)).toBe('{"key": "value"}');
    });

    it('should strip ``` code fence without language', () => {
      const input = '```\n{"key": "value"}\n```';
      expect(service.extractJson(input)).toBe('{"key": "value"}');
    });

    it('should extract JSON from text with preamble', () => {
      const input = 'Here is the analysis:\n{"key": "value"}';
      const result = service.extractJson(input);
      expect(JSON.parse(result)).toEqual({ key: 'value' });
    });

    it('should extract JSON array', () => {
      const input = '[{"a": 1}, {"b": 2}]';
      expect(service.extractJson(input)).toBe('[{"a": 1}, {"b": 2}]');
    });

    it('should handle nested JSON', () => {
      const input = '{"outer": {"inner": {"deep": true}}}';
      const result = service.extractJson(input);
      expect(JSON.parse(result)).toEqual({ outer: { inner: { deep: true } } });
    });

    it('should handle JSON with trailing text', () => {
      const input = 'Result: {"key": "value"} end of response';
      const result = service.extractJson(input);
      expect(JSON.parse(result)).toEqual({ key: 'value' });
    });

    it('should handle empty string', () => {
      expect(service.extractJson('')).toBe('');
    });

    it('should handle whitespace-only string', () => {
      expect(service.extractJson('   ')).toBe('');
    });

    it('should handle complex nested JSON with arrays', () => {
      const input = '{"recommendations": ["a", "b"], "data": {"items": [1, 2, 3]}}';
      const result = service.extractJson(input);
      expect(JSON.parse(result)).toEqual({
        recommendations: ['a', 'b'],
        data: { items: [1, 2, 3] }
      });
    });
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
        createVideo('1', 'バズ動画', 500000, 5000),
        createVideo('2', '普通動画', 10000, 10000),
        createVideo('3', 'まあまあ動画', 30000, 10000),
      ];

      const result = await service.detectBuzz(videos);
      expect(result.success).toBe(true);

      const ranking = result.data!.ranking;
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

    it('should handle zero subscribers', async () => {
      const videos = [createVideo('1', 'ゼロ登録者', 1000, 0)];
      const result = await service.detectBuzz(videos);
      expect(result.data!.ranking[0].buzzLevel).toBe('unknown');
    });
  });
});
