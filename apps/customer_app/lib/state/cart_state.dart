import 'package:flutter/foundation.dart';
import 'package:hb_shared/hb_shared.dart';

/// A cart can only hold items from one vendor at a time, matching how a
/// single COD order is placed against a single vendor.
class CartState extends ChangeNotifier {
  VendorDetail? _vendor;
  final Map<String, int> _quantities = {};

  VendorDetail? get vendor => _vendor;
  bool get isEmpty => _quantities.isEmpty;
  int get itemCount => _quantities.values.fold(0, (sum, q) => sum + q);

  int quantityOf(String itemId) => _quantities[itemId] ?? 0;

  double get total {
    if (_vendor == null) return 0;
    final byId = {for (final item in _vendor!.allItems) item.id: item};
    return _quantities.entries.fold<double>(0, (sum, e) {
      final item = byId[e.key];
      return sum + (item?.price ?? 0) * e.value;
    });
  }

  /// True if adding from [vendor] would conflict with what's already in the
  /// cart (i.e. the cart is non-empty and belongs to a different vendor).
  bool conflictsWith(VendorDetail vendor) => _vendor != null && _vendor!.id != vendor.id && !isEmpty;

  void add(MenuItem item, VendorDetail vendor) {
    if (conflictsWith(vendor)) {
      _quantities.clear();
    }
    _vendor = vendor;
    _quantities[item.id] = (_quantities[item.id] ?? 0) + 1;
    notifyListeners();
  }

  void removeOne(MenuItem item) {
    final current = _quantities[item.id] ?? 0;
    if (current <= 1) {
      _quantities.remove(item.id);
    } else {
      _quantities[item.id] = current - 1;
    }
    if (_quantities.isEmpty) _vendor = null;
    notifyListeners();
  }

  void clear() {
    _quantities.clear();
    _vendor = null;
    notifyListeners();
  }

  List<Map<String, dynamic>> toOrderItems() =>
      _quantities.entries.map((e) => {'menu_item_id': e.key, 'quantity': e.value}).toList();
}
