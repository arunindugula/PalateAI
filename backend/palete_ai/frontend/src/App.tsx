import ChatWidget from './components/ChatWidget'
import './App.css'

const HIGHLIGHTS = [
  {
    name: 'Hot & Sour Soup',
    description: 'Tangy, peppery, Indo-Chinese comfort in a bowl. Veg or chicken.',
  },
  {
    name: 'Rava Dosa',
    description: 'Crispy, lacy semolina crepe — no fermentation required.',
  },
  {
    name: 'Chicken 65',
    description: 'Spiced, fried, and fiery — a South Indian classic starter.',
  },
  {
    name: 'Hakka Noodles',
    description: 'Stir-fried thin noodles, Indo-Chinese seasoning, your choice of protein.',
  },
]

function App() {
  return (
    <>
      <header className="site-header">
        <div className="wrap">
          <span className="brand">Palete</span>
          <nav>
            <a href="#menu">Menu</a>
            <a href="#hours">Hours</a>
          </nav>
        </div>
      </header>

      <section className="hero">
        <div className="wrap">
          <h1>South Indian &amp; Indo-Chinese, made to order.</h1>
          <p>
            Soups, dosas, pakoda, Hakka noodles — ask our assistant anything about the
            menu, or track an order you've already placed.
          </p>
        </div>
      </section>

      <section className="highlights" id="menu">
        <div className="wrap">
          <h2>A few favorites</h2>
          <div className="cards">
            {HIGHLIGHTS.map((item) => (
              <article className="card" key={item.name}>
                <h3>{item.name}</h3>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
          <p className="hint">Curious about anything else? Our assistant knows the full menu — just ask.</p>
        </div>
      </section>

      <section className="hours" id="hours">
        <div className="wrap">
          <h2>Hours &amp; Location</h2>
          <p>Mon&ndash;Sun · 11:00am &ndash; 10:00pm</p>
          <p>123 Curry Lane, Flavor Town</p>
        </div>
      </section>

      <footer className="site-footer">
        <div className="wrap">&copy; 2026 Palete. All rights reserved.</div>
      </footer>

      <ChatWidget />
    </>
  )
}

export default App
