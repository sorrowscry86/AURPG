// Dart mirrors of all Pydantic server schemas.

class ClockSnapshot {
  final String id;
  final String label;
  final String clockType;
  final int segments;
  final int filled;

  const ClockSnapshot({
    required this.id,
    required this.label,
    required this.clockType,
    required this.segments,
    required this.filled,
  });

  factory ClockSnapshot.fromJson(Map<String, dynamic> j) => ClockSnapshot(
        id: j['id'] as String,
        label: j['label'] as String,
        clockType: j['clock_type'] as String,
        segments: j['segments'] as int,
        filled: j['filled'] as int,
      );
}

class StateSnapshot {
  final int stress;
  final int momentum;
  final String harm;
  final List<ClockSnapshot> clocks;

  const StateSnapshot({
    required this.stress,
    required this.momentum,
    required this.harm,
    required this.clocks,
  });

  factory StateSnapshot.fromJson(Map<String, dynamic> j) => StateSnapshot(
        stress: j['stress'] as int,
        momentum: j['momentum'] as int,
        harm: j['harm'] as String,
        clocks: (j['clocks'] as List<dynamic>)
            .map((e) => ClockSnapshot.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  StateSnapshot copyWith({int? stress, int? momentum, String? harm, List<ClockSnapshot>? clocks}) =>
      StateSnapshot(
        stress: stress ?? this.stress,
        momentum: momentum ?? this.momentum,
        harm: harm ?? this.harm,
        clocks: clocks ?? this.clocks,
      );
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

class SessionSummary {
  final String id;
  final String model;
  final String lastSaved;
  final int turnCount;
  final String? characterName;

  const SessionSummary({
    required this.id,
    required this.model,
    required this.lastSaved,
    required this.turnCount,
    this.characterName,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> j) => SessionSummary(
        id: j['id'] as String,
        model: j['model'] as String,
        lastSaved: j['last_saved'] as String,
        turnCount: j['turn_count'] as int,
        characterName: j['character_name'] as String?,
      );
}

class SessionCreateResponse {
  final String sessionId;
  final StateSnapshot state;

  const SessionCreateResponse({required this.sessionId, required this.state});

  factory SessionCreateResponse.fromJson(Map<String, dynamic> j) =>
      SessionCreateResponse(
        sessionId: j['session_id'] as String,
        state: StateSnapshot.fromJson(j['state'] as Map<String, dynamic>),
      );
}

class SessionStateResponse {
  final int stress;
  final int momentum;
  final String harm;
  final List<ClockSnapshot> clocks;
  final List<Map<String, dynamic>> turnHistory;

  const SessionStateResponse({
    required this.stress,
    required this.momentum,
    required this.harm,
    required this.clocks,
    required this.turnHistory,
  });

  factory SessionStateResponse.fromJson(Map<String, dynamic> j) =>
      SessionStateResponse(
        stress: j['stress'] as int,
        momentum: j['momentum'] as int,
        harm: j['harm'] as String,
        clocks: (j['clocks'] as List<dynamic>)
            .map((e) => ClockSnapshot.fromJson(e as Map<String, dynamic>))
            .toList(),
        turnHistory: (j['turn_history'] as List<dynamic>)
            .map((e) => e as Map<String, dynamic>)
            .toList(),
      );
}

class WizardConfigBody {
  final String title;
  final String genre;
  final String tone;
  final String canonMode;
  final String characterName;
  final int edge;
  final int heart;
  final int iron;
  final int shadow;
  final int wits;
  final String load;
  final Map<String, String> safety;
  final String orchestrationMode;
  final String initialPosition;
  final String initialEffect;

  const WizardConfigBody({
    required this.title,
    required this.genre,
    required this.tone,
    required this.canonMode,
    required this.characterName,
    required this.edge,
    required this.heart,
    required this.iron,
    required this.shadow,
    required this.wits,
    required this.load,
    required this.safety,
    required this.orchestrationMode,
    required this.initialPosition,
    required this.initialEffect,
  });

  Map<String, dynamic> toJson() => {
        'title': title,
        'genre': genre,
        'tone': tone,
        'canon_mode': canonMode,
        'character_name': characterName,
        'edge': edge,
        'heart': heart,
        'iron': iron,
        'shadow': shadow,
        'wits': wits,
        'load': load,
        'safety': safety,
        'orchestration_mode': orchestrationMode,
        'initial_position': initialPosition,
        'initial_effect': initialEffect,
      };
}

// ---------------------------------------------------------------------------
// Turns
// ---------------------------------------------------------------------------

class SafetyEvent {
  final String command;
  final String oocText;

  const SafetyEvent({required this.command, required this.oocText});

  factory SafetyEvent.fromJson(Map<String, dynamic> j) => SafetyEvent(
        command: j['command'] as String,
        oocText: j['ooc_text'] as String,
      );
}

class TurnResponse {
  final String rawText;
  final List<String> options;
  final String? ledgerBlock;
  final StateSnapshot state;
  final SafetyEvent? safetyEvent;

  const TurnResponse({
    required this.rawText,
    required this.options,
    this.ledgerBlock,
    required this.state,
    this.safetyEvent,
  });

  factory TurnResponse.fromJson(Map<String, dynamic> j) => TurnResponse(
        rawText: j['raw_text'] as String,
        options: (j['options'] as List<dynamic>).cast<String>(),
        ledgerBlock: j['ledger_block'] as String?,
        state: StateSnapshot.fromJson(j['state'] as Map<String, dynamic>),
        safetyEvent: j['safety_event'] != null
            ? SafetyEvent.fromJson(j['safety_event'] as Map<String, dynamic>)
            : null,
      );
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

class AppSettings {
  final String provider;
  final bool apiKeySet;
  final String apiKeyPreview;
  final String model;
  final String savesDir;
  final int port;

  const AppSettings({
    required this.provider,
    required this.apiKeySet,
    required this.apiKeyPreview,
    required this.model,
    required this.savesDir,
    required this.port,
  });

  factory AppSettings.fromJson(Map<String, dynamic> j) => AppSettings(
        provider: j['provider'] as String,
        apiKeySet: j['api_key_set'] as bool,
        apiKeyPreview: j['api_key_preview'] as String,
        model: j['model'] as String,
        savesDir: j['saves_dir'] as String,
        port: j['port'] as int,
      );
}

class ModelInfo {
  final String id;
  final String name;
  final int contextLength;
  final String provider;

  const ModelInfo({
    required this.id,
    required this.name,
    required this.contextLength,
    required this.provider,
  });

  factory ModelInfo.fromJson(Map<String, dynamic> j) => ModelInfo(
        id: j['id'] as String,
        name: j['name'] as String,
        contextLength: j['context_length'] as int,
        provider: j['provider'] as String,
      );
}

class ModelsResponse {
  final String provider;
  final List<ModelInfo> models;

  const ModelsResponse({required this.provider, required this.models});

  factory ModelsResponse.fromJson(Map<String, dynamic> j) => ModelsResponse(
        provider: j['provider'] as String,
        models: (j['models'] as List<dynamic>)
            .map((e) => ModelInfo.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class HealthResponse {
  final String status;
  final String version;

  const HealthResponse({required this.status, required this.version});

  factory HealthResponse.fromJson(Map<String, dynamic> j) => HealthResponse(
        status: j['status'] as String,
        version: j['version'] as String,
      );
}
