from PIL import Image
import operator

class Unshredder:

    shreds = 40
    shred_width = 16

    def __init__(self, source_image):
        print 'unshreding %s' % source_image
        self.image_shreds = []
        self.source_image = Image.open(source_image)
        
    def get_pixel_value(self, image, x, y):
        data = image.getdata()
        width, height = image.size
        pixel = data[y * width + x]
        return pixel

    def get_side_pixels(self, image):
        left_pixels = []
        right_pixels = []
        w, h = image.size

        for i in range(0, h):
            left_pixels.append(self.get_pixel_value(image, 0, i))
            right_pixels.append(self.get_pixel_value(image, w-1, i))

        return left_pixels, right_pixels

    def score_similar_colors(self, color1, color2):
        return (abs(color1[0]-color2[0]) + abs(color1[1]-color2[1]) + abs(color1[2]-color2[2])) / 3

    def score_lines(self, line1, line2):
        total_pixcels = len(line1)
        total_diff = 0

        for i in range(0, total_pixcels):
            total_diff += self.score_similar_colors(line1[i], line2[i])

        return total_diff / total_pixcels

    def score_similar_shreds(self, left_shred, right_shred):
        return self.score_lines(left_shred['right_pixels'], right_shred['left_pixels'])

    def run_it_baby(self):
        width, height = self.source_image.size
        self.find_shreds()

        for i in range(0, self.shreds):
            shred_dict = {'id':i}
            x1, y1 = i * self.shred_width, 0
            x2, y2 = i * self.shred_width + self.shred_width, height
            shred = self.source_image.crop((x1, y1, x2, y2))
            shred_image = Image.new('RGBA', (self.shred_width, height))
            shred_image.paste(shred, (0, 0))
            shred_dict['image'] = shred_image
            left_pixels, right_pixels = self.get_side_pixels(shred_image)
            shred_dict['left_pixels'] = left_pixels
            shred_dict['right_pixels'] = right_pixels
            shred_dict['match_shreds'] = []
            self.image_shreds.append(shred_dict)

        self.compare_and_score_shreds()
        return unshredder.connect()

    def compare_and_score_shreds(self):
        for left_shred in self.image_shreds:
            match_shreds = []
            for right_shred in self.image_shreds:
                if right_shred['id'] != left_shred['id']:
                    score = self.score_similar_shreds(left_shred, right_shred)
                    match_shred = {'id':right_shred['id'], 'score':score}
                    match_shreds.append(match_shred)

            match_shreds.sort(key=operator.itemgetter('score'))
            left_shred['match_shreds'] = match_shreds

        for shred in self.image_shreds:
            self.check_for_duplicates(shred)
            
    def check_for_duplicates(self, compare_shred):
        for shred in self.image_shreds:
            if shred['id'] != compare_shred['id']:
                compare_right = compare_shred['match_shreds'][0]
                right = shred['match_shreds'][0]
                if compare_right['id'] == right['id']:
                    if compare_right['score'] < right['score']:
                        del shred['match_shreds'][0]
                        self.check_for_duplicates(shred)
                    else:
                        del compare_shred['match_shreds'][0]
                        self.check_for_duplicates(compare_shred)

    def find_left_shred(self, sid):
        for shred in self.image_shreds:
            if shred['match_shreds'][0]['id'] == sid:
                return shred

    def connect(self):
        self.used_shreds = []
        self.chain = []
        max_diff = 0
        edge_position = 0

        for pos, item in enumerate(self.image_shreds):
            score_left = self.find_left_shred(item['id'])['match_shreds'][0]['score']
            current_score = item['match_shreds'][0]['score']
            score_right = self.image_shreds[item['match_shreds'][0]['id']]['match_shreds'][0]['score']
            diff = abs(current_score - score_left) + abs(current_score - score_right)

            if diff > max_diff:
                max_diff = diff
                edge_position = pos

        self.build_chain(self.image_shreds[self.image_shreds[edge_position]['match_shreds'][0]['id']])

        beauty = Image.new('RGBA', self.source_image.size)

        for pos, item in enumerate(self.chain):
            beauty.paste(item['image'], (self.shred_width*pos, 0))

        return beauty

    def build_chain(self, shred):
        if shred['id'] not in self.used_shreds:
            self.used_shreds.append(shred['id'])
            self.chain.append(shred)
            self.build_chain(self.image_shreds[shred['match_shreds'][0]['id']])

    def find_shreds(self):
        lines = []
        w,h = self.source_image.size

        for i in range(0, w):
            line = []
            for j in range(0, h):
                line.append(self.get_pixel_value(self.source_image, i, j))
            lines.append(line)

        scores = []
        total = 0

        for (i, line) in enumerate(lines):
            if i < w-1:
                score = self.score_lines(line, lines[i+1])
                total += score
                scores.append(score)

        avg = total / len(scores)
        diffs = []
        total = 0
        
        for (i, score) in enumerate(scores):
            if i < len(scores) - 1:
                diff = abs(score - scores[i+1])
                if diff <= avg:
                    diff = 0
                else:
                    diff = 1
                diffs.append(diff)

        possible_widths = []
        width = 0

        for (i, diff) in enumerate(diffs):
            if i < len(diffs) - 1:
                width += 1

                if diff == 1:
                    if diffs[i+1] == 1:
                        possible_widths.append(width)
                    else:
                        width = 0

        possible_widths = [(x, possible_widths.count(x)) for x in set(possible_widths)]

        possible_widths.sort(key=operator.itemgetter(1), reverse=True)
        
        shred_width = possible_widths[0]
        self.shred_width = shred_width[0] + 1
        self.shreds = w / self.shred_width

        print '%d shreds with width %d' %(self.shreds, self.shred_width)

for i in range(0, 16):
    unshredder = Unshredder('shredded/%d.png'%i)
    img = unshredder.run_it_baby()
    img.save('unshredded/%d.png'%i)