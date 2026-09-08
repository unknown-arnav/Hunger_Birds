enum UserRole {
  customer,
  vendor,
  admin;

  static UserRole fromJson(String value) => UserRole.values.firstWhere(
        (e) => e.name == value,
        orElse: () => UserRole.customer,
      );
}

class AppUser {
  final String id;
  final String email;
  final String? fullName;
  final UserRole role;

  const AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as String,
        email: json['email'] as String,
        fullName: json['full_name'] as String?,
        role: UserRole.fromJson(json['role'] as String),
      );
}
