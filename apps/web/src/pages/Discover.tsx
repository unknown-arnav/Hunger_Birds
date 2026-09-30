import { useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';
import type { Vendor } from '../lib/types';
import StallCard from '../components/StallCard';
import { EmptyState, ErrorRetry, Icon, PageLoader } from '../components/ui';
import { useAuth } from '../state/AuthContext';

type Filter = 'all' | 'open';

export default function Discover() {
  const { user } = useAuth();
  const [vendors, setVendors] = useState<Vendor[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Filter>('all');

  async function load() {
    setError(null);
    setVendors(null);
    try {
      setVendors(await api.listVendors());
    } catch {
      setError("Couldn't load the stalls. Check your connection.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const visible = useMemo(() => {
    if (!vendors) return [];
    const needle = query.trim().toLowerCase();
    return vendors
      .filter((v) => (filter === 'open' ? v.is_open : true))
      .filter(
        (v) =>
          !needle ||
          v.stall_name.toLowerCase().includes(needle) ||
          (v.description ?? '').toLowerCase().includes(needle),
      )
      // Open stalls first - a closed one is a dead end for the customer.
      .sort((a, b) => Number(b.is_open) - Number(a.is_open));
  }, [vendors, query, filter]);

  const openCount = vendors?.filter((v) => v.is_open).length ?? 0;
  const firstName = user?.full_name?.split(' ')[0];

  return (
    <div className="pb-space-xl">
      {/* The red band continues out of the header, so the search sits inside
          the brand strip rather than starting the dark page. This is the one
          loud element; everything below it stays quiet. */}
      <section className="bg-primary pb-space-lg md:pb-space-md">
        <div className="mx-auto max-w-content px-margin-mobile md:px-margin">
          <h1 className="pb-space-md text-display-hero-mobile text-white md:text-headline-lg">
            {firstName ? `Hungry, ${firstName}?` : 'Hungry?'}
          </h1>

          {/* Capped, because a search field stretched across 1200px of red
              reads as a banner rather than as something to type into. */}
          <label className="flex h-14 max-w-2xl items-center gap-space-sm rounded-xl bg-surface-container-lowest px-space-md">
            <Icon name="search" className="text-[22px] text-primary" />
            <input
              className="w-full bg-transparent text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none"
              placeholder="Search stalls or dishes"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {query && (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => setQuery('')}
                className="flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
              >
                <Icon name="close" className="text-[18px]" />
              </button>
            )}
          </label>
        </div>
      </section>

      <div className="mx-auto max-w-content px-margin-mobile md:px-margin">
        {/* Chip row. Horizontally scrolling on a narrow screen, the way the
            app's filter row behaves. */}
        <div className="no-scrollbar -mx-margin-mobile flex gap-space-sm overflow-x-auto px-margin-mobile py-space-lg md:mx-0 md:px-0">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`pill ${filter === 'all' ? 'pill-active' : ''}`}
          >
            All stalls
          </button>
          <button
            type="button"
            onClick={() => setFilter('open')}
            className={`pill ${filter === 'open' ? 'pill-active' : ''}`}
          >
            <Icon name="schedule" className="text-[16px]" />
            Open now
          </button>
          {vendors && vendors.length > 0 && (
            <span className="pill pointer-events-none border-transparent bg-transparent text-on-surface-variant">
              {openCount} of {vendors.length} open
            </span>
          )}
        </div>

        <h2 className="section-eyebrow pb-space-md">
          {filter === 'open' ? 'Open right now' : 'Stalls on campus'}
        </h2>

        {error ? (
          <ErrorRetry message={error} onRetry={load} />
        ) : !vendors ? (
          <PageLoader />
        ) : visible.length === 0 ? (
          <EmptyState
            icon="storefront"
            title={query ? 'Nothing matched that' : 'No stalls yet'}
            message={
              query
                ? 'Try a different search, or clear the filters.'
                : 'Once an admin approves the first stall, it shows up here.'
            }
          />
        ) : (
          <div className="grid grid-cols-2 gap-x-space-md gap-y-space-lg lg:grid-cols-4">
            {visible.map((vendor) => (
              <StallCard key={vendor.id} vendor={vendor} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
