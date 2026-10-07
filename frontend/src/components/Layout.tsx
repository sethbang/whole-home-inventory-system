  import React, { Fragment } from 'react';
  import whisLogo from '../assets/whis_logo.svg';
import { Link, useLocation } from 'react-router-dom';
import { Disclosure, Menu, Transition } from '@headlessui/react';
import {
  Bars3Icon,
  ComputerDesktopIcon,
  MoonIcon,
  SunIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/useAuth';
import { useDevMode } from '../contexts/useDevMode';
import { useTheme } from '../contexts/useTheme';
import type { ThemeMode } from '../contexts/ThemeContext';

const navigation = [
  { name: 'Dashboard', href: '/' },
  { name: 'Browse', href: '/browse' },
  { name: 'Add Item', href: '/items/new' },
  { name: 'Reports', href: '/reports' },
  { name: 'Backups', href: '/backups' },
];

// v3.2: admin-only entries are merged into ``navigation`` at render time
// when ``user.is_admin`` is true. Keeping them out of the base array means
// non-admin users never see the link.
const adminNavigation = [
  { name: 'Settings', href: '/settings' },
];

const themeOptions: Array<{
  mode: ThemeMode;
  label: string;
  shortLabel: string;
  Icon: typeof SunIcon;
}> = [
  { mode: 'day', label: 'Day', shortLabel: 'Day', Icon: SunIcon },
  { mode: 'night', label: 'Night', shortLabel: 'Night', Icon: MoonIcon },
  { mode: 'system', label: 'System-sync', shortLabel: 'System', Icon: ComputerDesktopIcon },
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

function ThemeSegmentedControl({ size }: { size: 'sm' | 'md' }) {
  const { mode, setMode } = useTheme();
  const buttonPad = size === 'sm' ? 'px-2 py-1.5 text-xs' : 'px-3 py-2 text-sm';
  return (
    <div
      role="radiogroup"
      aria-label="Color theme"
      className="flex items-center gap-1 rounded-md border border-line bg-surface-muted p-1"
    >
      {themeOptions.map(({ mode: optionMode, label, shortLabel, Icon }) => {
        const isActive = mode === optionMode;
        return (
          <button
            key={optionMode}
            type="button"
            role="radio"
            aria-checked={isActive}
            aria-label={label}
            title={label}
            onClick={() => setMode(optionMode)}
            className={classNames(
              'inline-flex flex-1 items-center justify-center gap-1.5 rounded font-medium transition-colors',
              buttonPad,
              isActive
                ? 'bg-primary-subtle text-primary shadow-sm'
                : 'text-muted hover:bg-surface-raised hover:text-fg',
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            <span>{shortLabel}</span>
          </button>
        );
      })}
    </div>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { isDevMode, toggleDevMode } = useDevMode();
  const location = useLocation();
  const visibleNavigation = user?.is_admin
    ? [...navigation, ...adminNavigation]
    : navigation;

  return (
    <div className="min-h-screen bg-surface-muted">
      <Disclosure as="nav" className="bg-surface-raised shadow-sm">
        {({ open }) => (
          <>
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="flex h-16 justify-between">
                <div className="flex">
                  <div className="flex flex-shrink-0 items-center">
                    <Link to="/" className="flex items-center">
                      <img src={whisLogo} alt="WHIS Logo" className="h-16 w-16" />
                    </Link>
                  </div>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    {visibleNavigation.map((item) => (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={classNames(
                          location.pathname === item.href
                            ? 'border-primary text-fg'
                            : 'border-transparent text-subtle hover:border-line-strong hover:text-muted',
                          'inline-flex items-center border-b-2 px-1 pt-1 text-sm font-medium'
                        )}
                      >
                        {item.name}
                      </Link>
                    ))}
                  </div>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:items-center">
                  <Menu as="div" className="relative ml-3">
                    <div>
                      <Menu.Button className="flex rounded-full bg-surface-raised text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                        <span className="sr-only">Open user menu</span>
                        <div className="h-8 w-8 rounded-full bg-primary-subtle-hover flex items-center justify-center">
                          <span className="text-primary-hover font-medium">
                            {user?.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      </Menu.Button>
                    </div>
                    <Transition
                      as={Fragment}
                      enter="transition ease-out duration-200"
                      enterFrom="transform opacity-0 scale-95"
                      enterTo="transform opacity-100 scale-100"
                      leave="transition ease-in duration-75"
                      leaveFrom="transform opacity-100 scale-100"
                      leaveTo="transform opacity-0 scale-95"
                    >
                      <Menu.Items className="absolute right-0 z-10 mt-2 w-64 origin-top-right rounded-md bg-surface-raised py-2 shadow-lg ring-1 ring-overlay/5 focus:outline-none">
                        <div className="px-3 pb-2">
                          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-subtle">
                            Theme
                          </div>
                          <ThemeSegmentedControl size="sm" />
                        </div>
                        <div className="my-1 border-t border-line" />
                        <Menu.Item>
                          {({ active }) => (
                            <button
                              onClick={toggleDevMode}
                              className={classNames(
                                active ? 'bg-surface-muted' : '',
                                'block w-full px-4 py-2 text-left text-sm text-muted'
                              )}
                            >
                              {isDevMode ? 'Disable Dev Mode' : 'Enable Dev Mode'}
                            </button>
                          )}
                        </Menu.Item>
                        <Menu.Item>
                          {({ active }) => (
                            <button
                              onClick={logout}
                              className={classNames(
                                active ? 'bg-surface-muted' : '',
                                'block w-full px-4 py-2 text-left text-sm text-muted'
                              )}
                            >
                              Sign out
                            </button>
                          )}
                        </Menu.Item>
                      </Menu.Items>
                    </Transition>
                  </Menu>
                </div>
                <div className="-mr-2 flex items-center sm:hidden">
                  <Disclosure.Button className="inline-flex items-center justify-center rounded-md bg-surface-raised p-2 text-subtle hover:bg-surface-muted hover:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                    <span className="sr-only">Open main menu</span>
                    {open ? (
                      <XMarkIcon className="block h-6 w-6" aria-hidden="true" />
                    ) : (
                      <Bars3Icon className="block h-6 w-6" aria-hidden="true" />
                    )}
                  </Disclosure.Button>
                </div>
              </div>
            </div>

            <Disclosure.Panel className="sm:hidden">
              <div className="space-y-1 pb-3 pt-2">
                {visibleNavigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={classNames(
                      location.pathname === item.href
                        ? 'bg-primary-subtle border-primary text-primary-hover'
                        : 'border-transparent text-muted hover:bg-surface-muted hover:border-line-strong hover:text-fg',
                      'block border-l-4 py-2 pl-3 pr-4 text-base font-medium'
                    )}
                  >
                    {item.name}
                  </Link>
                ))}
              </div>
              <div className="border-t border-line pb-3 pt-4">
                <div className="flex items-center px-4">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-primary-subtle-hover flex items-center justify-center">
                      <span className="text-primary-hover font-medium">
                        {user?.username.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <div className="text-base font-medium text-fg">
                      {user?.username}
                    </div>
                    <div className="text-sm font-medium text-subtle">
                      {user?.email}
                    </div>
                  </div>
                </div>
                <div className="mt-3 px-4">
                  <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-subtle">
                    Theme
                  </div>
                  <ThemeSegmentedControl size="md" />
                </div>
                <div className="mt-3 space-y-1">
                  <button
                    onClick={toggleDevMode}
                    className="block w-full px-4 py-2 text-left text-base font-medium text-subtle hover:bg-surface-muted hover:text-fg"
                  >
                    {isDevMode ? 'Disable Dev Mode' : 'Enable Dev Mode'}
                  </button>
                  <button
                    onClick={logout}
                    className="block w-full px-4 py-2 text-left text-base font-medium text-subtle hover:bg-surface-muted hover:text-fg"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </Disclosure.Panel>
          </>
        )}
      </Disclosure>

      <div className="py-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">{children}</div>
      </div>

      {/* Mobile Quick Add FAB */}
      {isDevMode && (
        <div className="sm:hidden">
          <Link
            to="/items/new"
            className="fixed bottom-6 right-6 h-14 w-14 rounded-full bg-primary flex items-center justify-center text-white shadow-lg hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
            aria-label="Add new item"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
          </Link>
        </div>
      )}
    </div>
  );
}
