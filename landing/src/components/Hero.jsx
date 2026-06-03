import HeroPlatform from './landing/HeroPlatform'
import HeroCompact from './landing/HeroCompact'
import { HERO_COMPACT_TITLES } from './landing/heroCompactTitles'

export default function Hero({ page = 'home' }) {
  if (page === 'home') return <HeroPlatform />
  if (HERO_COMPACT_TITLES[page]) return <HeroCompact page={page} />
  return <HeroCompact page="features" />
}
