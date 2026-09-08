import 'menu.dart';

class Vendor {
  final String id;
  final String stallName;
  final String? description;
  final String? coverImageUrl;
  final bool isApproved;
  final bool isOpen;

  const Vendor({
    required this.id,
    required this.stallName,
    required this.description,
    required this.coverImageUrl,
    required this.isApproved,
    required this.isOpen,
  });

  factory Vendor.fromJson(Map<String, dynamic> json) => Vendor(
        id: json['id'] as String,
        stallName: json['stall_name'] as String,
        description: json['description'] as String?,
        coverImageUrl: json['cover_image_url'] as String?,
        isApproved: json['is_approved'] as bool,
        isOpen: json['is_open'] as bool,
      );
}

class VendorDetail extends Vendor {
  final List<CategoryWithItems> categories;
  final List<MenuItem> uncategorizedItems;

  const VendorDetail({
    required super.id,
    required super.stallName,
    required super.description,
    required super.coverImageUrl,
    required super.isApproved,
    required super.isOpen,
    required this.categories,
    required this.uncategorizedItems,
  });

  factory VendorDetail.fromJson(Map<String, dynamic> json) => VendorDetail(
        id: json['id'] as String,
        stallName: json['stall_name'] as String,
        description: json['description'] as String?,
        coverImageUrl: json['cover_image_url'] as String?,
        isApproved: json['is_approved'] as bool,
        isOpen: json['is_open'] as bool,
        categories: (json['categories'] as List)
            .map((e) => CategoryWithItems.fromJson(e as Map<String, dynamic>))
            .toList(),
        uncategorizedItems: (json['uncategorized_items'] as List)
            .map((e) => MenuItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  /// All menu items on this vendor, flattened, for quick lookups (e.g. cart).
  List<MenuItem> get allItems => [
        for (final c in categories) ...c.items,
        ...uncategorizedItems,
      ];
}
