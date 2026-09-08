import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:hb_shared/hb_shared.dart';
import 'package:provider/provider.dart';

import '../../state/cart_state.dart';
import '../../widgets/menu_item_tile.dart';
import '../cart/cart_screen.dart';

class VendorDetailScreen extends StatefulWidget {
  final String vendorId;

  const VendorDetailScreen({super.key, required this.vendorId});

  @override
  State<VendorDetailScreen> createState() => _VendorDetailScreenState();
}

class _VendorDetailScreenState extends State<VendorDetailScreen> {
  late Future<VendorDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiClient>().vendorDetail(widget.vendorId);
  }

  void _reload() {
    setState(() => _future = context.read<ApiClient>().vendorDetail(widget.vendorId));
  }

  Future<void> _handleAdd(MenuItem item, VendorDetail vendor) async {
    final cart = context.read<CartState>();
    if (cart.conflictsWith(vendor)) {
      final replace = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Start a new order?'),
          content: Text(
            'Your cart has items from ${cart.vendor!.stallName}. '
            'Adding this will clear that cart.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Keep it'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Start new'),
            ),
          ],
        ),
      );
      if (replace != true) return;
    }
    cart.add(item, vendor);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder<VendorDetail>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: AppTheme.primaryRed));
          }
          if (snapshot.hasError) {
            return SafeArea(
              child: ErrorRetry(message: snapshot.error.toString(), onRetry: _reload),
            );
          }

          final vendor = snapshot.data!;
          final cart = context.watch<CartState>();
          final sections = [
            for (final category in vendor.categories)
              if (category.items.isNotEmpty) (category.name, category.items),
            if (vendor.uncategorizedItems.isNotEmpty) ('More items', vendor.uncategorizedItems),
          ];

          return CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: 210,
                pinned: true,
                backgroundColor: AppTheme.surface,
                flexibleSpace: FlexibleSpaceBar(
                  background: _Cover(vendor: vendor),
                ),
              ),
              SliverToBoxAdapter(child: _VendorHeader(vendor: vendor)),
              if (sections.isEmpty)
                const SliverFillRemaining(
                  hasScrollBody: false,
                  child: EmptyState(
                    icon: Icons.restaurant_menu,
                    title: 'Menu coming soon',
                    message: 'This stall hasn\'t added any items yet.',
                  ),
                )
              else
                SliverList.builder(
                  itemCount: sections.length,
                  itemBuilder: (context, i) {
                    final (title, items) = sections[i];
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 20, 16, 4),
                          child: Text(
                            '$title (${items.length})',
                            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Column(
                            children: [
                              for (final item in items) ...[
                                MenuItemTile(
                                  item: item,
                                  quantity: cart.quantityOf(item.id),
                                  orderingEnabled: vendor.isOpen,
                                  onAdd: () => _handleAdd(item, vendor),
                                  onRemove: () => context.read<CartState>().removeOne(item),
                                ),
                                if (item != items.last) const Divider(height: 1),
                              ],
                            ],
                          ),
                        ),
                      ],
                    );
                  },
                ),
              const SliverToBoxAdapter(child: SizedBox(height: 90)),
            ],
          );
        },
      ),
      bottomNavigationBar: const _CartBar(),
    );
  }
}

class _Cover extends StatelessWidget {
  final VendorDetail vendor;

  const _Cover({required this.vendor});

  @override
  Widget build(BuildContext context) {
    if (vendor.coverImageUrl == null || vendor.coverImageUrl!.isEmpty) {
      return Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFFFB199), Color(0xFFE23744)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
      );
    }
    return CachedNetworkImage(
      imageUrl: vendor.coverImageUrl!,
      fit: BoxFit.cover,
      placeholder: (_, __) => Container(color: AppTheme.divider),
      errorWidget: (_, __, ___) => Container(color: AppTheme.divider),
    );
  }
}

class _VendorHeader extends StatelessWidget {
  final VendorDetail vendor;

  const _VendorHeader({required this.vendor});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.surface,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            vendor.stallName,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
          ),
          if (vendor.description != null && vendor.description!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              vendor.description!,
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14, height: 1.4),
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: (vendor.isOpen ? AppTheme.success : AppTheme.textSecondary)
                      .withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  vendor.isOpen ? 'Open now' : 'Closed right now',
                  style: TextStyle(
                    color: vendor.isOpen ? AppTheme.success : AppTheme.textSecondary,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppTheme.divider,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'Cash on delivery',
                  style: TextStyle(
                    color: AppTheme.textSecondary,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CartBar extends StatelessWidget {
  const _CartBar();

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartState>();
    if (cart.isEmpty) return const SizedBox.shrink();

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: Material(
          color: AppTheme.primaryRed,
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const CartScreen()),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
              child: Row(
                children: [
                  Text(
                    '${cart.itemCount} item${cart.itemCount == 1 ? '' : 's'}  ·  '
                    '₹${cart.total.toStringAsFixed(0)}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                  ),
                  const Spacer(),
                  const Text(
                    'View cart',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Icon(Icons.arrow_forward, color: Colors.white, size: 18),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
