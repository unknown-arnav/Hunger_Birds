import { NavLink } from 'react-router-dom';
import { Icon } from './ui';

/**
 * The floating tab bar from the Zomato app: a dark pill that sits above the
 * content rather than sticking to the edge of the screen.
 *
 * Phone only. On a wide screen the same destinations are already in the header
 * nav, and a floating bar there would be a second navigation for the same three
 * routes. These are the app's actual destinations - the reference has Delivery
 * and Dining because that app has them; adding a tab that leads nowhere would
 * be borrowing the shape without the substance.
 */
const tabs = [
  { to: '/', label: 'Explore', icon: 'storefront', end: true },
  { to: '/orders', label: 'Orders', icon: 'receipt_long', end: false },
  { to: '/profile', label: 'Profile', icon: 'person', end: false },
];

export default function BottomNav() {
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 flex justify-center px-margin-mobile pb-[max(0.75rem,env(safe-area-inset-bottom))] xl:hidden"
    >
      <div className="flex w-full max-w-sm items-center gap-space-xs rounded-full border border-outline bg-surface-container-lowest p-space-xs shadow-nav">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-[2px] rounded-full px-space-sm py-space-sm text-label-sm transition-colors ${
                isActive
                  ? 'bg-primary-tint text-primary'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  name={tab.icon}
                  className={`text-[22px] ${isActive ? 'text-primary' : ''}`}
                />
                {tab.label}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
