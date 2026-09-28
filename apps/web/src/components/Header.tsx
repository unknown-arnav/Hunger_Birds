import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../state/AuthContext';
import { useCart } from '../state/CartContext';
import { Icon } from './ui';

/**
 * The red brand band.
 *
 * Zomato runs one saturated red strip across the top and keeps everything
 * below it near-black, so the red reads as chrome rather than as a section of
 * the page. It carries where you are collecting from, the cart, and the
 * account - and nothing else, because anything more turns the strip into a
 * second navigation layer competing with the content underneath.
 */
export default function Header() {
  const { user, isAdmin, signOut } = useAuth();
  const { count } = useCart();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const navLink = ({ isActive }: { isActive: boolean }) =>
    isActive
      ? 'text-label-lg text-white font-bold transition-colors'
      : 'text-label-lg text-white/70 hover:text-white transition-colors';

  const initial = (user?.full_name ?? user?.email ?? '?').charAt(0).toUpperCase();

  return (
    <header className="fixed inset-x-0 top-0 z-50 bg-primary">
      <div className="mx-auto flex h-20 max-w-content items-center justify-between gap-gutter px-margin-mobile md:px-margin">
        <div className="flex min-w-0 shrink items-center gap-gutter">
          <Link to="/" className="flex shrink-0 items-center gap-space-sm">
            <img src="/logo.png" alt="" width={36} height={36} className="h-9 w-9" />
            <span className="hidden flex-col leading-none sm:flex">
              <span className="text-headline-sm tracking-tight text-white">Hungry Birds</span>
              <span className="text-label-sm uppercase tracking-wide text-white/75">
                BIT Mesra Campus
              </span>
            </span>
          </Link>

          {/* Zomato's address selector. This is campus pickup rather than
              delivery, so it names the collection point instead of offering a
              list of addresses to switch between. */}
          <div className="flex min-w-0 flex-col leading-tight">
            <span className="flex items-center gap-space-xs text-label-lg text-white">
              <Icon name="storefront" className="text-[18px]" />
              Pick up
            </span>
            <span className="truncate text-body-sm text-white/75">At the stall counter</span>
          </div>
        </div>

        <nav className="hidden items-center gap-space-lg xl:flex">
          <NavLink to="/" end className={navLink}>
            Explore
          </NavLink>
          <NavLink to="/orders" className={navLink}>
            Orders
          </NavLink>
          {isAdmin && (
            <NavLink to="/admin" className={navLink}>
              Admin
            </NavLink>
          )}
        </nav>

        <div className="flex shrink-0 items-center gap-space-sm">
          <button
            type="button"
            aria-label="Cart"
            onClick={() => navigate('/checkout')}
            className="relative flex h-10 w-10 items-center justify-center rounded-full bg-white/15 transition-colors hover:bg-white/25"
          >
            <Icon name="shopping_bag" className="text-[22px] text-white" />
            {count > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-white px-space-xs text-label-sm text-primary">
                {count}
              </span>
            )}
          </button>

          <div className="relative">
            <button
              type="button"
              aria-label="Account menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-label-lg text-primary transition-transform hover:scale-105"
            >
              {initial}
            </button>

            {menuOpen && (
              <>
                {/* Click-away layer, so the menu closes on any outside tap. */}
                <button
                  type="button"
                  aria-hidden
                  tabIndex={-1}
                  className="fixed inset-0 z-10 cursor-default"
                  onClick={() => setMenuOpen(false)}
                />
                <div className="absolute right-0 z-20 mt-space-sm w-60 overflow-hidden rounded-lg border border-outline bg-surface-container-lowest shadow-sheet">
                  <div className="border-b border-outline-variant px-space-md py-space-sm">
                    <p className="truncate text-label-lg text-on-surface">
                      {user?.full_name ?? 'Campus foodie'}
                    </p>
                    <p className="truncate text-body-sm text-on-surface-variant">{user?.email}</p>
                  </div>
                  <Link
                    to="/profile"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-space-sm px-space-md py-space-sm text-body-sm text-on-surface-medium hover:bg-surface-container hover:text-on-surface"
                  >
                    <Icon name="person" className="text-[18px]" /> Profile
                  </Link>
                  <Link
                    to="/orders"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-space-sm px-space-md py-space-sm text-body-sm text-on-surface-medium hover:bg-surface-container hover:text-on-surface"
                  >
                    <Icon name="receipt_long" className="text-[18px]" /> My orders
                  </Link>
                  {isAdmin && (
                    <Link
                      to="/admin"
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-space-sm px-space-md py-space-sm text-body-sm text-on-surface-medium hover:bg-surface-container hover:text-on-surface"
                    >
                      <Icon name="shield_person" className="text-[18px]" /> Admin panel
                    </Link>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      void signOut();
                    }}
                    className="flex w-full items-center gap-space-sm border-t border-outline-variant px-space-md py-space-sm text-left text-body-sm text-primary hover:bg-surface-container"
                  >
                    <Icon name="logout" className="text-[18px]" /> Log out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
