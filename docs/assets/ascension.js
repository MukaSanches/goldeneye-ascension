(() => {
  const nav = document.querySelector('.nav');
  const update = () => nav?.classList.toggle('scrolled', window.scrollY > 24);
  update();
  addEventListener('scroll', update, { passive: true });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('[data-reveal]').forEach((el) => observer.observe(el));
})();
