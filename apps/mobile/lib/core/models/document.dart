class DocumentJob {
  const DocumentJob({required this.id, required this.originalFilename, required this.contentType, required this.documentFormat, required this.sourceLanguage, required this.sizeBytes, required this.status, required this.progress, required this.pageCount, required this.ocrPages, required this.errorCode, required this.errorMessage, required this.expiresAt, this.targetLanguage, this.translationCharacters = 0, this.outputContentType, this.outputFilename});

  factory DocumentJob.fromJson(Map<String, dynamic> json) => DocumentJob(
        id: json['id'] as String,
        originalFilename: json['original_filename'] as String,
        contentType: json['content_type'] as String,
        documentFormat: json['document_format'] as String,
        sourceLanguage: json['source_language'] as String?,
        sizeBytes: json['size_bytes'] as int,
        status: json['status'] as String,
        progress: (json['progress'] as num?)?.toInt() ?? 0,
        pageCount: (json['page_count'] as num?)?.toInt(),
        ocrPages: (json['ocr_pages'] as List<dynamic>? ?? const []).map((item) => (item as num).toInt()).toList(),
        errorCode: json['error_code'] as String?,
        errorMessage: json['error_message'] as String?,
        expiresAt: DateTime.parse(json['expires_at'] as String),
        targetLanguage: json['target_language'] as String?,
        translationCharacters: (json['translation_characters'] as num?)?.toInt() ?? 0,
        outputContentType: json['output_content_type'] as String?,
        outputFilename: json['output_filename'] as String?,
      );

  final String id;
  final String originalFilename;
  final String contentType;
  final String documentFormat;
  final String? sourceLanguage;
  final int sizeBytes;
  final String status;
  final int progress;
  final int? pageCount;
  final List<int> ocrPages;
  final String? errorCode;
  final String? errorMessage;
  final DateTime expiresAt;
  final String? targetLanguage;
  final int translationCharacters;
  final String? outputContentType;
  final String? outputFilename;

  bool get isActive => const {'queued', 'extracting', 'translating', 'exporting'}.contains(status);
  bool get isTerminal => const {'completed', 'failed', 'cancelled', 'expired'}.contains(status);
  bool get isReviewable => status == 'awaiting_review';

  DocumentJob copyWith({String? sourceLanguage, String? targetLanguage, String? status, int? progress, String? errorCode, String? errorMessage, String? outputContentType, String? outputFilename}) => DocumentJob(
        id: id,
        originalFilename: originalFilename,
        contentType: contentType,
        documentFormat: documentFormat,
        sourceLanguage: sourceLanguage ?? this.sourceLanguage,
        sizeBytes: sizeBytes,
        status: status ?? this.status,
        progress: progress ?? this.progress,
        pageCount: pageCount,
        ocrPages: ocrPages,
        errorCode: errorCode ?? this.errorCode,
        errorMessage: errorMessage ?? this.errorMessage,
        expiresAt: expiresAt,
        targetLanguage: targetLanguage ?? this.targetLanguage,
        translationCharacters: translationCharacters,
        outputContentType: outputContentType ?? this.outputContentType,
        outputFilename: outputFilename ?? this.outputFilename,
      );
}

class DocumentSegment {
  const DocumentSegment({required this.id, required this.index, required this.sourceText, required this.translatedText, required this.kind, required this.page, required this.location, this.blockIndex});

  factory DocumentSegment.fromJson(Map<String, dynamic> json) => DocumentSegment(
        id: json['id'] as String,
        index: (json['index'] as num).toInt(),
        sourceText: json['source_text'] as String,
        translatedText: json['translated_text'] as String?,
        kind: json['kind'] as String? ?? 'paragraph',
        page: (json['page'] as num?)?.toInt(),
        location: json['location'] as String?,
        blockIndex: (json['block_index'] as num?)?.toInt(),
      );

  final String id;
  final int index;
  final String sourceText;
  final String? translatedText;
  final String kind;
  final int? page;
  final String? location;
  final int? blockIndex;

  Map<String, dynamic> toJson() => {'id': id, 'index': index, 'source_text': sourceText, 'translated_text': translatedText, 'kind': kind, 'page': page, 'location': location, 'block_index': blockIndex};

  DocumentSegment copyWith({String? sourceText, Object? translatedText = _unset}) => DocumentSegment(id: id, index: index, sourceText: sourceText ?? this.sourceText, translatedText: translatedText == _unset ? this.translatedText : translatedText as String?, kind: kind, page: page, location: location, blockIndex: blockIndex);
}

const _unset = Object();

class DocumentSegmentsResponse {
  const DocumentSegmentsResponse({required this.jobId, required this.status, required this.segments});

  factory DocumentSegmentsResponse.fromJson(Map<String, dynamic> json) => DocumentSegmentsResponse(jobId: json['job_id'] as String, status: json['status'] as String, segments: (json['segments'] as List<dynamic>? ?? const []).map((item) => DocumentSegment.fromJson(Map<String, dynamic>.from(item as Map))).toList());

  final String jobId;
  final String status;
  final List<DocumentSegment> segments;
}

class DocumentDownload {
  const DocumentDownload({required this.bytes, required this.filename, required this.contentType});

  final List<int> bytes;
  final String filename;
  final String contentType;
}
