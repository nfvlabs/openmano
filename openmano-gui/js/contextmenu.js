/**
https://github.com/joewalnes/jquery-simple-context-menu
Copyright (c) 2011, Joe Walnes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/

jQuery.fn.contextPopup = function(menuData) {

	// Build popup menu HTML
	function createMenu() {
		var menu = $('<ul class=contextMenuPlugin><div class=gutterLine></div></ul>')
			.appendTo(document.body);
	    if (menuData.title) {
	    	$('<li class=header></li>').text(menuData.title).appendTo(menu);
	    }
	    menuData.items.forEach(function(item) {
	    	if (item) {
	    		var row = $('<li><a href="#"><img><span></span></a></li>').appendTo(menu);
	    		row.find('img').attr('src', item.icon);
	    		row.find('span').text(item.label);
	    		if (item.action) {
	    			row.find('a').click(item.action);
	    		}
	    	} else {
	    		$('<li class=divider></li>').appendTo(menu);
	    	}
	    });
	    menu.find('.header').text(menuData.title);
	    return menu;
	}

    function createandshow(e) {

    // Create and show menu
    var menu = createMenu()
      .show()
      .css({zIndex:1000001, left:e.pageX + 5 /* nudge to the right, so the pointer is covering the title */, top:e.pageY})
      .bind('contextmenu', function() { return false; });

    // Cover rest of page with invisible div that when clicked will cancel the popup.
    var bg = $('<div></div>')
      .css({left:0, top:0, width:'100%', height:'100%', position:'absolute', zIndex:1000000})
      .appendTo(document.body)
      .bind('contextmenu click', function() {
        // If click or right click anywhere else on page: remove clean up.
        bg.remove();
        menu.remove();
        return false;
      });

    // When clicking on a link in menu: clean up (in addition to handlers on link already)
    menu.find('a').click(function() {
      bg.remove();
      menu.remove();
    });

    // Cancel event, so real browser popup doesn't appear.
    return false;
  }
  // On contextmenu event (default right click)
  //console.log(menuData.button);
  if (menuData.button == "left")
  { this.click( function(e){ createandshow(e)});} else {this.bind('contextmenu', function(e){ createandshow(e)}); };

  return this;
};

