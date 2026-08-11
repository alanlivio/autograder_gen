public class Solution {
    public static Object add(Object... args) {
        if (args.length == 2) {
            int a = Integer.parseInt(args[0].toString());
            int b = Integer.parseInt(args[1].toString());
            return a - b;
        }
        return null;
    }
}
