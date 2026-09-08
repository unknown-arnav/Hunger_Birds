import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:hb_shared/hb_shared.dart';

class MenuItemTile extends StatelessWidget {
  final MenuItem item;
  final int quantity;
  final bool orderingEnabled;
  final VoidCallback onAdd;
  final VoidCallback onRemove;

  const MenuItemTile({
    super.key,
    required this.item,
    required this.quantity,
    required this.orderingEnabled,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    final unavailable = !item.isAvailable;

    return Opacity(
      opacity: unavailable ? 0.5 : 1,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.name,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '₹${item.price.toStringAsFixed(0)}',
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                  ),
                  if (item.description != null && item.description!.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      item.description!,
                      style: const TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 13,
                        height: 1.35,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 14),
            Column(
              children: [
                if (item.imageUrl != null && item.imageUrl!.isNotEmpty)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: CachedNetworkImage(
                      imageUrl: item.imageUrl!,
                      width: 96,
                      height: 84,
                      fit: BoxFit.cover,
                      placeholder: (_, __) =>
                          Container(width: 96, height: 84, color: AppTheme.divider),
                      errorWidget: (_, __, ___) =>
                          Container(width: 96, height: 84, color: AppTheme.divider),
                    ),
                  ),
                const SizedBox(height: 8),
                SizedBox(
                  width: 96,
                  child: unavailable
                      ? const _OutOfStockChip()
                      : _AddControl(
                          quantity: quantity,
                          enabled: orderingEnabled,
                          onAdd: onAdd,
                          onRemove: onRemove,
                        ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _OutOfStockChip extends StatelessWidget {
  const _OutOfStockChip();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 7),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppTheme.divider,
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Text(
        'Out of stock',
        style: TextStyle(color: AppTheme.textSecondary, fontWeight: FontWeight.w700, fontSize: 12),
      ),
    );
  }
}

class _AddControl extends StatelessWidget {
  final int quantity;
  final bool enabled;
  final VoidCallback onAdd;
  final VoidCallback onRemove;

  const _AddControl({
    required this.quantity,
    required this.enabled,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    if (quantity == 0) {
      return OutlinedButton(
        onPressed: enabled ? onAdd : null,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 7),
          side: BorderSide(color: enabled ? AppTheme.primaryRed : AppTheme.divider),
          foregroundColor: AppTheme.primaryRed,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: const Text('ADD', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
      );
    }

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: AppTheme.primaryRed),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _StepperButton(icon: Icons.remove, onTap: onRemove),
          Text(
            '$quantity',
            style: const TextStyle(
              color: AppTheme.primaryRed,
              fontWeight: FontWeight.w800,
              fontSize: 14,
            ),
          ),
          _StepperButton(icon: Icons.add, onTap: onAdd),
        ],
      ),
    );
  }
}

class _StepperButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _StepperButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
        child: Icon(icon, size: 17, color: AppTheme.primaryRed),
      ),
    );
  }
}
