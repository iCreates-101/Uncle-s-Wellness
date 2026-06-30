// POS System - Point of Sale Terminal
(function() {
  'use strict';

  let cart = [];
  let selectedMethod = 'cash';
  let searchTimeout = null;

  // DOM refs
  const posProducts = document.getElementById('posProducts');
  const posCart = document.getElementById('posCart');
  const posSearch = document.getElementById('posSearch');
  const posSearchResults = document.getElementById('posSearchResults');
  const posClearCart = document.getElementById('posClearCart');
  const posCheckout = document.getElementById('posCheckout');
  const posItemCount = document.getElementById('posItemCount');
  const posSubtotal = document.getElementById('posSubtotal');
  const posTax = document.getElementById('posTax');
  const posTotal = document.getElementById('posTotal');
  const posAmountTendered = document.getElementById('posAmountTendered');
  const posChange = document.getElementById('posChange');
  const posCustomerName = document.getElementById('posCustomerName');
  const posCustomerPhone = document.getElementById('posCustomerPhone');
  const receiptModal = document.getElementById('receiptModal');
  const receiptDetails = document.getElementById('receiptDetails');
  const receiptLink = document.getElementById('receiptLink');

  // ─── Add product to cart ──────────────────────────────────
  function addToCart(id, name, price, stock, qty) {
    qty = qty || 1;
    if (stock < qty) {
      alert('Not enough stock! Available: ' + stock);
      return;
    }
    var existing = null;
    for (var i = 0; i < cart.length; i++) {
      if (String(cart[i].id) === String(id)) { existing = cart[i]; break; }
    }
    if (existing) {
      if (existing.quantity + qty > stock) {
        alert('Not enough stock! Available: ' + stock);
        return;
      }
      existing.quantity += qty;
    } else {
      cart.push({ id: String(id), name: name, price: price, stock: stock, quantity: qty });
    }
    renderCart();
    posSearch.value = '';
    posSearchResults.style.display = 'none';
  }

  // ─── Render cart ──────────────────────────────────────────
  function renderCart() {
    if (cart.length === 0) {
      posCart.innerHTML = '<div class="pos-cart-empty"><i class="fas fa-cart-plus"></i><p>Click products or scan barcode to add items</p></div>';
      posCheckout.disabled = true;
      posItemCount.textContent = '0';
      posSubtotal.textContent = '$0.00';
      posTax.textContent = '$0.00';
      posTotal.textContent = '$0.00';
      return;
    }

    let html = '';
    let totalItems = 0;
    let subtotal = 0;

    cart.forEach(function(item, idx) {
      totalItems += item.quantity;
      subtotal += item.price * item.quantity;
      html += '<div class="pos-cart-item">' +
        '<span class="pos-cart-item-name">' + item.name + '</span>' +
        '<div class="pos-cart-item-qty">' +
          '<button onclick="window.posDecQty(' + idx + ')">-</button>' +
          '<span>' + item.quantity + '</span>' +
          '<button onclick="window.posIncQty(' + idx + ')">+</button>' +
        '</div>' +
        '<span class="pos-cart-item-price">$' + (item.price * item.quantity).toFixed(2) + '</span>' +
        '<span class="pos-cart-item-remove" onclick="window.posRemoveItem(' + idx + ')"><i class="fas fa-times"></i></span>' +
      '</div>';
    });

    posCart.innerHTML = html;
    posCheckout.disabled = false;

    var tax = subtotal * 0.08;
    var total = subtotal + tax;

    posItemCount.textContent = totalItems;
    posSubtotal.textContent = '$' + subtotal.toFixed(2);
    posTax.textContent = '$' + tax.toFixed(2);
    posTotal.textContent = '$' + total.toFixed(2);

    calcChange();
  }

  // ─── Quantity controls ────────────────────────────────────
  window.posDecQty = function(idx) {
    if (cart[idx].quantity > 1) {
      cart[idx].quantity--;
    } else {
      cart.splice(idx, 1);
    }
    renderCart();
  };

  window.posIncQty = function(idx) {
    if (cart[idx].quantity < cart[idx].stock) {
      cart[idx].quantity++;
      renderCart();
    } else {
      alert('Maximum stock reached!');
    }
  };

  window.posRemoveItem = function(idx) {
    cart.splice(idx, 1);
    renderCart();
  };

  // ─── Calculate change ─────────────────────────────────────
  function calcChange() {
    var total = 0;
    cart.forEach(function(item) { total += item.price * item.quantity; });
    total += total * 0.08;
    var tendered = parseFloat(posAmountTendered.value);
    if (tendered && tendered >= total) {
      posChange.textContent = 'Change: $' + (tendered - total).toFixed(2);
      posChange.style.color = '#28a745';
    } else if (tendered && tendered < total) {
      posChange.textContent = 'Insufficient: $' + (total - tendered).toFixed(2) + ' short';
      posChange.style.color = '#dc3545';
    } else {
      posChange.textContent = '';
    }
  }

  if (posAmountTendered) {
    posAmountTendered.addEventListener('input', calcChange);
  }

  // ─── Product click events ─────────────────────────────────
  if (posProducts) {
    posProducts.addEventListener('click', function(e) {
      var target = e.target.closest('.pos-product');
      if (!target) return;
      var id = target.dataset.id;
      var name = target.dataset.name;
      var price = parseFloat(target.dataset.price);
      var stock = parseInt(target.dataset.stock);
      addToCart(id, name, price, stock, 1);
    });
  }

  // ─── Category filter ──────────────────────────────────────
  document.querySelectorAll('.cat-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.cat-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var cat = btn.dataset.cat;
      document.querySelectorAll('.pos-product').forEach(function(p) {
        if (cat === 'all' || p.dataset.cat === cat) {
          p.style.display = '';
        } else {
          p.style.display = 'none';
        }
      });
    });
  });

  // ─── Search / barcode scan ────────────────────────────────
  if (posSearch) {
    posSearch.addEventListener('input', function() {
      var q = posSearch.value.trim();
      if (q.length < 1) {
        posSearchResults.style.display = 'none';
        return;
      }
      // Try barcode lookup first
      fetch('/admin/pos/product/' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(product) {
          if (product) {
            addToCart(product.id, product.name, product.price, product.stock, 1);
            posSearchResults.style.display = 'none';
            return;
          }
          // Otherwise search
          fetch('/admin/pos/search?q=' + encodeURIComponent(q))
            .then(function(r) { return r.json(); })
            .then(function(results) {
              if (results.length === 0) {
                posSearchResults.style.display = 'none';
                return;
              }
              var html = '';
              results.forEach(function(p) {
                html += '<div onclick="window.posSelectSearch(' + p.id + ',\'' + p.name.replace(/'/g, "\\'") + '\',' + p.price + ',' + p.stock + ')">' +
                  p.name + ' - $' + p.price.toFixed(2) + ' <small>Stock: ' + p.stock + '</small></div>';
              });
              posSearchResults.innerHTML = html;
              posSearchResults.style.display = 'block';
            });
        });
    });

    posSearch.addEventListener('blur', function() {
      setTimeout(function() { posSearchResults.style.display = 'none'; }, 200);
    });

    posSearch.addEventListener('focus', function() {
      if (posSearchResults.children.length > 0) {
        posSearchResults.style.display = 'block';
      }
    });
  }

  window.posSelectSearch = function(id, name, price, stock) {
    addToCart(String(id), name, price, stock, 1);
    posSearchResults.style.display = 'none';
  };

  // ─── Payment method ───────────────────────────────────────
  document.querySelectorAll('.pay-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.pay-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      selectedMethod = btn.dataset.method;
      var cashInput = document.getElementById('posCashInput');
      if (selectedMethod === 'cash') {
        cashInput.style.display = 'block';
      } else {
        cashInput.style.display = 'none';
        posChange.textContent = '';
      }
    });
  });

  // ─── Clear cart ───────────────────────────────────────────
  if (posClearCart) {
    posClearCart.addEventListener('click', function() {
      if (cart.length === 0) return;
      if (confirm('Clear all items from current sale?')) {
        cart = [];
        renderCart();
        posSearch.value = '';
        posSearch.focus();
      }
    });
  }

  // ─── Checkout ─────────────────────────────────────────────
  if (posCheckout) {
    posCheckout.addEventListener('click', function() {
      if (cart.length === 0) {
        alert('Cart is empty');
        return;
      }

      var total = 0;
      cart.forEach(function(item) { total += item.price * item.quantity; });
      total += total * 0.08;

      var tendered = parseFloat(posAmountTendered.value) || total;

      if (selectedMethod === 'cash' && tendered < total) {
        alert('Amount tendered is less than total!');
        return;
      }

      var payload = {
        items: cart.map(function(item) { return { id: item.id, quantity: item.quantity }; }),
        payment_method: selectedMethod,
        customer_name: posCustomerName ? posCustomerName.value.trim() || 'Walk-in Customer' : 'Walk-in Customer',
        customer_phone: posCustomerPhone ? posCustomerPhone.value.trim() : '',
        amount_tendered: tendered
      };

      posCheckout.disabled = true;
      posCheckout.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

      fetch('/admin/pos/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(function(r) { return r.json(); })
      .then(function(result) {
        if (result.error) {
          alert(result.error);
          posCheckout.disabled = false;
          posCheckout.innerHTML = '<i class="fas fa-check-circle"></i> Complete Sale';
          return;
        }
        showReceipt(result);
        cart = [];
        renderCart();
        posSearch.value = '';
        posSearch.focus();
      })
      .catch(function(err) {
        alert('Checkout error: ' + err.message);
        posCheckout.disabled = false;
        posCheckout.innerHTML = '<i class="fas fa-check-circle"></i> Complete Sale';
      });
    });
  }

  // ─── Show receipt ─────────────────────────────────────────
  function showReceipt(data) {
    var itemsHtml = '';
    data.items.forEach(function(item) {
      itemsHtml += '<div class="receipt-detail-item"><span>' + item.product_name + ' x' + item.quantity + '</span><span>$' + item.total.toFixed(2) + '</span></div>';
    });

    var changeHtml = '';
    if (data.change > 0) {
      changeHtml = '<div class="receipt-detail-item"><span>Change</span><span>$' + data.change.toFixed(2) + '</span></div>';
    }

    var methodLabel = data.payment_method === 'cash' ? 'Cash' : data.payment_method === 'card' ? 'Card' : 'Transfer';

    receiptDetails.innerHTML =
      '<p><strong>Order:</strong> ' + data.order_number + '</p>' +
      '<p><strong>Date:</strong> ' + new Date().toLocaleString() + '</p>' +
      '<p><strong>Customer:</strong> ' + data.customer_name + '</p>' +
      '<hr>' +
      itemsHtml +
      '<hr>' +
      '<div class="receipt-detail-item"><span>Subtotal</span><span>$' + data.subtotal.toFixed(2) + '</span></div>' +
      '<div class="receipt-detail-item"><span>Tax (8%)</span><span>$' + data.tax.toFixed(2) + '</span></div>' +
      '<div class="receipt-detail-item receipt-total-line"><span>Total</span><span>$' + data.total.toFixed(2) + '</span></div>' +
      '<div class="receipt-detail-item"><span>Paid (' + methodLabel + ')</span><span>$' + data.amount_tendered.toFixed(2) + '</span></div>' +
      changeHtml +
      '<hr>' +
      '<p style="text-align:center;color:#666;font-size:0.8rem">Thank you for shopping!</p>';

    receiptLink.href = '/admin/pos/receipt/' + data.order_id;
    receiptModal.style.display = 'block';
  }

  // ─── Close modal on outside click ─────────────────────────
  receiptModal.addEventListener('click', function(e) {
    if (e.target === receiptModal) {
      receiptModal.style.display = 'none';
    }
  });

  // ─── Keyboard shortcuts ───────────────────────────────────
  document.addEventListener('keydown', function(e) {
    // F8 or Ctrl+Enter to checkout
    if (e.key === 'F8' || (e.ctrlKey && e.key === 'Enter')) {
      e.preventDefault();
      if (!posCheckout.disabled) posCheckout.click();
    }
    // F2 to focus search
    if (e.key === 'F2') {
      e.preventDefault();
      if (posSearch) posSearch.focus();
    }
    // Escape to close modal
    if (e.key === 'Escape') {
      receiptModal.style.display = 'none';
    }
  });

  // Focus search on load
  if (posSearch) posSearch.focus();

})();
