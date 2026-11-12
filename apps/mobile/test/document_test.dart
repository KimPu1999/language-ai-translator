import 'package:flutter_test/flutter_test.dart';

import 'package:lingua_mobile/core/models/document.dart';

void main() {
  test('document job maps status, progress, expiry and output metadata', () {
    final job = DocumentJob.fromJson({
      'id': 'job-1',
      'original_filename': 'hello.txt',
      'content_type': 'text/plain',
      'document_format': 'txt',
      'source_language': null,
      'size_bytes': 12,
      'status': 'awaiting_review',
      'progress': 100,
      'page_count': 1,
      'ocr_pages': [],
      'error_code': null,
      'error_message': null,
      'expires_at': '2099-01-01T00:00:00Z',
      'target_language': 'my',
      'translation_characters': 12,
      'output_content_type': null,
      'output_filename': null,
    });

    expect(job.isReviewable, isTrue);
    expect(job.isActive, isFalse);
    expect(job.targetLanguage, 'my');
    expect(job.progress, 100);
  });

  test('document segment round-trips Burmese Unicode and review fields', () {
    const segment = DocumentSegment(id: 'segment-0-0', index: 0, sourceText: 'မင်္ဂလာပါ', translatedText: null, kind: 'paragraph', page: 1, location: null);
    final decoded = DocumentSegment.fromJson(segment.toJson());
    expect(decoded.sourceText, 'မင်္ဂလာပါ');
    expect(decoded.page, 1);
    expect(decoded.copyWith(sourceText: 'Hello').translatedText, isNull);
  });
}
