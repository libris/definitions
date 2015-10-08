$(function () {

  $('.link-item').each(function() {
    $(this).prepend('<div class="chip-expanded">'+ $(this).html() +'</div>');
    var chip = $(this).find('.chip-expanded');
    //var x = $(this).offset().left;
    //if (x + chip.width() > $(document.body).width()) {
    //  chip.css('right', 0);
    //}
  });

  $('.link-item').hover(function() {
    var chip = $(this).find('.chip-expanded');
    chip.addClass('to-be-active');
    setTimeout(function() {
      if(chip.hasClass('to-be-active'))
        chip.addClass('active').removeClass('to-be-active');
    }, 500);
  }, function() {
    var chip = $(this).find('.chip-expanded');
    chip.removeClass('active').removeClass('to-be-active');
  });

  $(document).ready(function () {
  });

});
