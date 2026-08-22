document.addEventListener('DOMContentLoaded', () => {
  const sliders = document.querySelectorAll('[data-slider]');

  sliders.forEach(cards => {
    const wrap = cards.closest('.slider-wrap');
    const section = cards.closest('.card-section');
    const dotsContainer = section.querySelector('.slider-dots');
    const prevBtn = wrap.querySelector('.prev');
    const nextBtn = wrap.querySelector('.next');

    const cardEls = Array.from(cards.children);
    const cardsPerSlide = 3;
    const slideCount = Math.ceil(cardEls.length / cardsPerSlide);

    if (slideCount <= 1) {
      if (dotsContainer) dotsContainer.remove();
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) nextBtn.style.display = 'none';
      return;
    }

    // build dots
    dotsContainer.innerHTML = '';
    const dots = [];
    for (let i = 0; i < slideCount; i++) {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
      if (i === 0) dot.classList.add('active');
      dot.addEventListener('click', () => goToSlide(i));
      dotsContainer.appendChild(dot);
      dots.push(dot);
    }

    let currentSlide = 0;

    function goToSlide(index) {
      currentSlide = Math.max(0, Math.min(index, slideCount - 1));
      const target = cardEls[currentSlide * cardsPerSlide];
      if (target) cards.scrollTo({ left: target.offsetLeft, behavior: 'smooth' });
    }

    function updateUI() {
      dots.forEach((dot, i) => dot.classList.toggle('active', i === currentSlide));
      prevBtn.disabled = currentSlide === 0;
      nextBtn.disabled = currentSlide === slideCount - 1;
    }

    prevBtn.addEventListener('click', () => { goToSlide(currentSlide - 1); });
    nextBtn.addEventListener('click', () => { goToSlide(currentSlide + 1); });

    let scrollTimeout;
    cards.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        let closestIndex = 0;
        let closestDistance = Infinity;

        cardEls.forEach((card, index) => {
          const distance = Math.abs(card.offsetLeft - cards.scrollLeft);
          if (distance < closestDistance) {
            closestDistance = distance;
            closestIndex = index;
          }
        });

        currentSlide = Math.round(closestIndex / cardsPerSlide);
        updateUI();
      }, 80);
    });

    updateUI();
  });
});