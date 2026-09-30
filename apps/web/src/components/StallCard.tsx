import { Link } from 'react-router-dom';
import type { Vendor } from '../lib/types';
import { placeholderGradient } from '../lib/format';
import { Icon } from './ui';

/**
 * A stall, in the shape Zomato gives a restaurant: photo with rounded corners
 * carrying a status pill, then name, then one line of quiet metadata.
 *
 * Zomato puts a rating badge and a discount strip on the photo. Neither exists
 * here - there are no ratings (out of scope) and no discounts (cash on pickup,
 * no payment integration) - so the slot those occupy carries the one status
 * that does change and does decide whether the card is worth tapping: whether
 * the stall is open. Inventing a rating to fill the space would be inventing
 * data.
 */
export default function StallCard({ vendor }: { vendor: Vendor }) {
  return (
    <Link
      to={`/stall/${vendor.id}`}
      className="group flex flex-col gap-space-sm focus-visible:outline-none"
    >
      <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-surface-container-lowest">
        {vendor.cover_image_url ? (
          <img
            src={vendor.cover_image_url}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div
            className={`flex h-full w-full items-center justify-center bg-gradient-to-br ${placeholderGradient(vendor.id)}`}
          >
            <Icon name="storefront" className="text-[40px] text-white/40" />
          </div>
        )}

        {/* Scrim, so a pale photo cannot swallow the pill sitting on it. */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/70 to-transparent" />

        <span
          className={`absolute bottom-space-sm left-space-sm inline-flex h-[22px] items-center gap-[3px] rounded px-[6px] text-label-sm ${
            vendor.is_open ? 'bg-success text-white' : 'bg-black/75 text-white/90'
          }`}
        >
          <Icon name={vendor.is_open ? 'schedule' : 'bedtime'} className="text-[13px]" />
          {vendor.is_open ? 'Open now' : 'Closed'}
        </span>
      </div>

      <div className="flex flex-col gap-[2px]">
        <h3 className="truncate text-headline-sm text-on-surface group-hover:text-primary">
          {vendor.stall_name}
        </h3>
        <p className="truncate text-body-sm text-on-surface-variant">
          {vendor.description ?? 'Freshly made on campus.'}
        </p>
        {/* Zomato's metadata row: small, grey, separated by a dot. It is the
            terms of the order, which is what a customer checks before tapping. */}
        <p className="truncate pt-[2px] text-label-md text-on-surface-variant">
          Pickup <span aria-hidden="true">·</span> Cash at counter
        </p>
      </div>
    </Link>
  );
}
