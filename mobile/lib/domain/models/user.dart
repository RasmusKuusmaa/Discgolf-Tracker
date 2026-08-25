import 'package:freezed_annotation/freezed_annotation.dart';

part 'user.freezed.dart';
part 'user.g.dart';

@freezed
abstract class User with _$User {
  const factory User({
    required String id,
    required String email,
    required String username,
    required String displayName,
    String? avatarUrl,
    String? homeCity,
    String? country,
    @Default('public') String profileVisibility,
    @Default('public') String statsVisibility,
    @Default(true) bool allowFriendRequests,
  }) = _User;

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
}
