// Main site functionality
document.addEventListener('DOMContentLoaded', function() {
  // Quantity selector buttons
  document.querySelectorAll('.quantity-selector').forEach(function(el) {
    const input = el.querySelector('input[type="number"]');
    if (!input) return;
    const dec = el.querySelector('button:first-of-type');
    const inc = el.querySelector('button:last-of-type');
    if (dec) dec.addEventListener('click', function() { if (parseInt(input.value) > 1) input.stepDown(); });
    if (inc) inc.addEventListener('click', function() { if (parseInt(input.value) < parseInt(input.max)) input.stepUp(); });
  });

  // Auto-dismiss alerts
  document.querySelectorAll('.alert').forEach(function(el) {
    setTimeout(function() { el.style.opacity = '0'; el.style.transition = 'opacity 0.3s'; }, 5000);
    setTimeout(function() { el.remove(); }, 5300);
  });
});
