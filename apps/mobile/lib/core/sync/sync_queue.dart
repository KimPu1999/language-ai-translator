import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/sync.dart';
import '../network/api_client.dart';

class SyncQueueState {
  const SyncQueueState({this.pending = 0, this.error});
  final int pending;
  final String? error;
}

class SyncQueueController extends StateNotifier<SyncQueueState> {
  SyncQueueController() : super(const SyncQueueState()) {
    _loadCount();
  }

  static const _key = 'lingua-sync-upload-queue';
  SharedPreferences? _preferences;

  Future<SharedPreferences> _prefs() async => _preferences ??= await SharedPreferences.getInstance();

  Future<List<Map<String, dynamic>>> _read() async {
    final prefs = await _prefs();
    return (prefs.getStringList(_key) ?? const []).map((value) => Map<String, dynamic>.from(jsonDecode(value) as Map)).toList();
  }

  Future<void> _loadCount() async => state = SyncQueueState(pending: (await _read()).length);

  Future<void> enqueue(String userId, List<SyncRecord> records) async {
    final entries = await _read();
    for (final record in records) {
      final key = '$userId:${record.entityType}:${record.clientRecordId}';
      entries.removeWhere((entry) => entry['key'] == key);
      entries.add({'key': key, 'user_id': userId, 'record': record.toJson()});
    }
    final prefs = await _prefs();
    await prefs.setStringList(_key, entries.map((entry) => jsonEncode(entry)).toList());
    state = SyncQueueState(pending: entries.length);
  }

  Future<void> flush(String userId, ApiClient api) async {
    final entries = await _read();
    final mine = entries.where((entry) => entry['user_id'] == userId).toList();
    if (mine.isEmpty) { state = SyncQueueState(pending: entries.length); return; }
    try {
      final records = mine.map((entry) => SyncRecord.fromJson(Map<String, dynamic>.from(entry['record'] as Map))).toList();
      await api.importSync(records, idempotencyKey: 'mobile-${DateTime.now().microsecondsSinceEpoch}');
      entries.removeWhere((entry) => entry['user_id'] == userId);
      final prefs = await _prefs();
      await prefs.setStringList(_key, entries.map((entry) => jsonEncode(entry)).toList());
      state = SyncQueueState(pending: entries.length);
    } on ApiFailure catch (error) {
      state = SyncQueueState(pending: entries.length, error: error.message);
    } catch (error) {
      state = SyncQueueState(pending: entries.length, error: error.toString());
    }
  }

  Future<void> clearForUser(String userId) async {
    final entries = await _read()..removeWhere((entry) => entry['user_id'] == userId);
    final prefs = await _prefs();
    await prefs.setStringList(_key, entries.map((entry) => jsonEncode(entry)).toList());
    state = SyncQueueState(pending: entries.length);
  }

  Future<void> clearAll() async {
    final prefs = await _prefs();
    await prefs.remove(_key);
    state = const SyncQueueState();
  }
}

final syncQueueProvider = StateNotifierProvider<SyncQueueController, SyncQueueState>((ref) => SyncQueueController());
